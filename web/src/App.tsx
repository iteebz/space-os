import { useState, useEffect, useMemo } from 'react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { BsArchive, BsArchiveFill } from 'react-icons/bs'
import {
  ChannelList,
  MessageList,
  ComposeBox,
  CreateChannel,
  ChannelHeader,
  AgentStatus,
  useChannels,
  useMessages,
  useMarkChannelRead,
  useHumanIdentity,
} from './features/channels'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { postApi } from './lib/api'
import { SessionStream } from './features/sessions'
import { useAgentMap } from './features/agents'
import { useSpawns } from './features/spawns'

interface AgentTab {
  agentId: string
  identity: string | null
  sessionId: string | null
  isRunning: boolean
}

export default function App() {
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [showArchived, setShowArchived] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [previousChannel, setPreviousChannel] = useState<string | null>(null)
  const { data: identity } = useHumanIdentity()
  const { data: channels } = useChannels(showArchived, identity?.identity)
  const { data: messages = [] } = useMessages(selectedChannel)
  const { mutate: markRead } = useMarkChannelRead()
  const { data: spawns } = useSpawns()
  const agentMap = useAgentMap()
  const queryClient = useQueryClient()

  const { mutate: createChannel, error: createError } = useMutation({
    mutationFn: ({ name, topic }: { name: string; topic: string | null }) =>
      postApi('/channels', { name, topic }),
    onSuccess: (_, { name }) => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
      setIsCreating(false)
      setSelectedChannel(name)
    },
  })

  const handleStartCreate = () => {
    setPreviousChannel(selectedChannel)
    setIsCreating(true)
    setSelectedChannel(null)
  }

  const handleCreateChannel = (name: string, topic: string | null) => {
    createChannel({ name, topic })
  }

  const handleCancelCreate = () => {
    setIsCreating(false)
    setSelectedChannel(previousChannel)
  }

  const handleSelectChannel = (name: string) => {
    setIsCreating(false)
    setSelectedChannel(name)
  }

  const currentChannel = channels?.find((c) => c.name === selectedChannel)

  const agentTabs = useMemo(() => {
    if (!currentChannel?.channel_id || !spawns) return []

    const agentSpawnsMap = new Map<
      string,
      { sessionId: string | null; isRunning: boolean; lastActivity: number }
    >()

    spawns
      .filter((s) => s.channel_id === currentChannel.channel_id)
      .forEach((s) => {
        const existing = agentSpawnsMap.get(s.agent_id)
        const spawnTime = new Date(s.created_at).getTime()
        const isRunning = s.status === 'running'

        if (!existing || spawnTime > existing.lastActivity || (isRunning && !existing.isRunning)) {
          agentSpawnsMap.set(s.agent_id, {
            sessionId: s.session_id,
            isRunning,
            lastActivity: spawnTime,
          })
        }
      })

    const tabs: AgentTab[] = []
    agentSpawnsMap.forEach((data, agentId) => {
      tabs.push({
        agentId,
        identity: agentMap.get(agentId) ?? null,
        sessionId: data.sessionId,
        isRunning: data.isRunning,
      })
    })

    return tabs.sort((a, b) => {
      if (a.isRunning && !b.isRunning) return -1
      if (!a.isRunning && b.isRunning) return 1
      return (a.identity ?? a.agentId).localeCompare(b.identity ?? b.agentId)
    })
  }, [currentChannel?.channel_id, spawns, agentMap])

  const selectedTab = agentTabs.find((t) => t.agentId === selectedAgentId) ?? agentTabs[0]

  useEffect(() => {
    if (agentTabs.length > 0 && !agentTabs.find((t) => t.agentId === selectedAgentId)) {
      const running = agentTabs.find((t) => t.isRunning)
      setSelectedAgentId(running?.agentId ?? agentTabs[0]?.agentId ?? null)
    }
  }, [agentTabs, selectedAgentId])

  useEffect(() => {
    setSelectedAgentId(null)
  }, [currentChannel?.channel_id])

  useEffect(() => {
    if (!selectedChannel && channels && channels.length > 0) {
      const sorted = [...channels].sort((a, b) => {
        if (!a.last_activity) return 1
        if (!b.last_activity) return -1
        return new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime()
      })
      setSelectedChannel(sorted[0].name)
    }
  }, [selectedChannel, channels])

  useEffect(() => {
    if (selectedChannel && identity?.identity && messages.length > 0) {
      markRead({ channel: selectedChannel, readerId: identity.identity })
    }
  }, [selectedChannel, messages.length, identity?.identity, markRead])

  const handleExportChannel = () => {
    if (!messages.length) return

    const text = messages
      .map((msg) => {
        const ident = agentMap.get(msg.agent_id) ?? msg.agent_id.slice(0, 7)
        const isoString = msg.created_at.endsWith('Z') ? msg.created_at : `${msg.created_at}Z`
        const timestamp = new Date(isoString).toLocaleString()
        return `[${timestamp}] ${ident}:\n${msg.content}\n`
      })
      .join('\n')

    void navigator.clipboard.writeText(text).then(() => {})
  }

  return (
    <div className="h-screen w-screen">
      <PanelGroup direction="horizontal">
        <Panel defaultSize={15} minSize={10}>
          <div className="h-full border-r border-neutral-800 p-4 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
                Channels
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowArchived(!showArchived)}
                  className={`p-1.5 rounded transition-colors ${
                    showArchived
                      ? 'text-cyan-400 hover:text-cyan-300'
                      : 'text-neutral-500 hover:text-neutral-400'
                  }`}
                  title={showArchived ? 'Show active channels' : 'Show archived channels'}
                >
                  {showArchived ? <BsArchiveFill size={16} /> : <BsArchive size={16} />}
                </button>
                <CreateChannel onClick={handleStartCreate} />
              </div>
            </div>
            <div className="flex-1 min-h-0">
              <ChannelList
                selected={selectedChannel}
                onSelect={handleSelectChannel}
                showArchived={showArchived}
                isCreating={false}
                onCreateChannel={() => {}}
                onCancelCreate={() => {}}
              />
            </div>
          </div>
        </Panel>

        <PanelResizeHandle className="w-1 bg-neutral-800 hover:bg-neutral-700 transition-colors" />

        <Panel defaultSize={42} minSize={25}>
          <div className="h-full p-4 flex flex-col">
            {isCreating ? (
              <ChannelHeader
                channel={{
                  name: '',
                  topic: null,
                  channel_id: '',
                  message_count: 0,
                  last_activity: null,
                  unread_count: 0,
                  archived_at: null,
                  pinned_at: null,
                }}
                isCreating={true}
                onCreate={handleCreateChannel}
                onCancelCreate={handleCancelCreate}
                createError={createError}
              />
            ) : selectedChannel && currentChannel ? (
              <>
                <ChannelHeader channel={currentChannel} onExportClick={handleExportChannel} />
                <div className="flex-1 overflow-y-auto scrollable">
                  <MessageList channelName={selectedChannel} channelId={currentChannel.channel_id} />
                </div>
                <AgentStatus channel={selectedChannel} />
                <ComposeBox channel={selectedChannel} />
              </>
            ) : (
              <div className="text-neutral-500">Select a channel</div>
            )}
          </div>
        </Panel>

        <PanelResizeHandle className="w-1 bg-neutral-800 hover:bg-neutral-700 transition-colors" />

        <Panel defaultSize={43} minSize={25}>
          <div className="h-full border-l border-neutral-800 flex flex-col">
            {agentTabs.length > 0 ? (
              <>
                <div className="flex border-b border-neutral-800 overflow-x-auto">
                  {agentTabs.map((tab) => (
                    <button
                      key={tab.agentId}
                      onClick={() => setSelectedAgentId(tab.agentId)}
                      className={`px-4 py-2 text-sm flex items-center gap-2 whitespace-nowrap border-b-2 transition-colors ${
                        selectedTab?.agentId === tab.agentId
                          ? 'border-cyan-500 text-white'
                          : 'border-transparent text-neutral-400 hover:text-neutral-200'
                      }`}
                    >
                      {tab.identity ?? tab.agentId.slice(0, 8)}
                      <span
                        className={`w-2 h-2 rounded-full ${
                          tab.isRunning ? 'bg-green-400' : 'bg-neutral-600'
                        }`}
                      />
                    </button>
                  ))}
                </div>

                <div className="flex-1 overflow-y-auto scrollable p-4">
                  {selectedTab?.sessionId ? (
                    <SessionStream sessionId={selectedTab.sessionId} />
                  ) : (
                    <div className="text-neutral-500 text-sm">Waiting for session...</div>
                  )}
                </div>
              </>
            ) : (
              <div className="p-4 text-neutral-500 text-sm">No agents in this channel</div>
            )}
          </div>
        </Panel>
      </PanelGroup>
    </div>
  )
}
