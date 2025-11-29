import { useEffect, useMemo, useState } from 'react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import {
  BsArchive,
  BsArchiveFill,
  BsList,
  BsChevronLeft,
  BsClipboard,
  BsCheck,
} from 'react-icons/bs'
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
import { SessionStream, ContextIndicator } from './features/sessions'
import { useAgentMap } from './features/agents'
import { useSpawns } from './features/spawns'
import { useUrlState } from './lib/useUrlState'
import { ErrorBoundary } from './lib/ErrorBoundary'

interface AgentTab {
  agentId: string
  identity: string | null
  sessionId: string | null
  isRunning: boolean
}

export default function App() {
  const [showChannelDrawer, setShowChannelDrawer] = useState(false)
  const [showSessionModal, setShowSessionModal] = useState(false)
  const [showMobileExportCopied, setShowMobileExportCopied] = useState(false)
  const { params, setParam } = useUrlState()
  const selectedChannel = params.get('channel')
  const showArchived = params.get('archived') === 'true'
  const isCreating = params.get('create') === 'true'
  const selectedAgentId = params.get('agent')

  const { data: identity } = useHumanIdentity()
  const { data: channels } = useChannels(showArchived, identity?.identity)

  const autoSelectedChannel = isCreating
    ? null
    : !selectedChannel && channels && channels.length > 0
      ? [...channels].sort((a, b) => {
          if (!a.last_activity) return 1
          if (!b.last_activity) return -1
          return new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime()
        })[0].name
      : selectedChannel

  const { data: messages = [] } = useMessages(autoSelectedChannel)
  const { mutate: markRead } = useMarkChannelRead()
  const { data: spawns } = useSpawns()
  const agentMap = useAgentMap()
  const queryClient = useQueryClient()

  const { mutate: createChannel, error: createError } = useMutation({
    mutationFn: ({ name, topic }: { name: string; topic: string | null }) =>
      postApi('/channels', { name, topic }),
    onSuccess: (_, { name }) => {
      queryClient.invalidateQueries({ queryKey: ['channels'] })
      setParam('create', null)
      setParam('channel', name)
    },
  })

  const currentChannel = channels?.find((c) => c.name === autoSelectedChannel)

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
      setParam('agent', running?.agentId ?? agentTabs[0]?.agentId ?? null)
    }
  }, [agentTabs, selectedAgentId, setParam])

  useEffect(() => {
    if (currentChannel?.channel_id) {
      setParam('agent', null)
    }
  }, [currentChannel?.channel_id, setParam])

  useEffect(() => {
    if (autoSelectedChannel && identity?.identity && messages.length > 0) {
      markRead({ channel: autoSelectedChannel, readerId: identity.identity })
    }
  }, [autoSelectedChannel, messages.length, identity?.identity, markRead])

  const handleExportChannel = async () => {
    if (!messages.length) return

    const text = messages
      .map((msg) => {
        const ident = agentMap.get(msg.agent_id) ?? msg.agent_id.slice(0, 7)
        const isoString = msg.created_at.endsWith('Z') ? msg.created_at : `${msg.created_at}Z`
        const timestamp = new Date(isoString).toLocaleString()
        return `[${timestamp}] ${ident}:\n${msg.content}\n`
      })
      .join('\n')

    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      const success = document.execCommand('copy')
      document.body.removeChild(textarea)
      return success
    }
  }

  const handleMobileExport = async () => {
    const success = await handleExportChannel()
    if (success) setShowMobileExportCopied(true)
  }

  useEffect(() => {
    if (showMobileExportCopied) {
      const timer = window.setTimeout(() => setShowMobileExportCopied(false), 2000)
      return () => window.clearTimeout(timer)
    }
  }, [showMobileExportCopied])

  return (
    <div className="h-screen w-screen overflow-hidden" style={{ height: '100dvh' }}>
      {showChannelDrawer && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setShowChannelDrawer(false)}
        />
      )}

      <div className="md:hidden fixed top-0 left-0 right-0 bg-neutral-900 border-b border-neutral-800 px-4 py-3 flex items-center gap-3 z-30">
        <button
          onClick={() => setShowChannelDrawer(true)}
          className="text-neutral-400 hover:text-white"
        >
          <BsList size={24} />
        </button>
        <div className="flex-1 text-white font-semibold truncate">
          # {autoSelectedChannel || 'Select channel'}
        </div>
        {currentChannel && messages.length > 0 && (
          <button
            onClick={handleMobileExport}
            className="text-neutral-400 hover:text-white"
            title={showMobileExportCopied ? 'Copied!' : 'Copy channel messages'}
          >
            {showMobileExportCopied ? <BsCheck size={20} /> : <BsClipboard size={18} />}
          </button>
        )}
      </div>

      {showSessionModal && selectedTab?.sessionId && (
        <div className="md:hidden fixed inset-0 bg-neutral-900 z-50 flex flex-col">
          <div className="border-b border-neutral-800 px-4 py-3 flex items-center gap-3">
            <button
              onClick={() => setShowSessionModal(false)}
              className="text-neutral-400 hover:text-white"
            >
              <BsChevronLeft size={20} />
            </button>
            <span className="text-white font-semibold">
              {selectedTab.identity ?? selectedTab.agentId.slice(0, 8)} Session
            </span>
          </div>
          <div className="flex-1 overflow-y-auto scrollable p-4">
            <ContextIndicator sessionId={selectedTab.sessionId} />
            <ErrorBoundary
              fallback={<div className="text-red-400 text-sm">Failed to load session</div>}
            >
              <SessionStream sessionId={selectedTab.sessionId} />
            </ErrorBoundary>
          </div>
        </div>
      )}

      <PanelGroup direction="horizontal">
        <Panel defaultSize={15} minSize={10} className="hidden md:block">
          <div className="h-full border-r border-neutral-800 p-4 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
                Channels
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setParam('archived', showArchived ? null : 'true')}
                  className={`p-1.5 rounded transition-colors ${
                    showArchived
                      ? 'text-cyan-400 hover:text-cyan-300'
                      : 'text-neutral-500 hover:text-neutral-400'
                  }`}
                  title={showArchived ? 'Show active channels' : 'Show archived channels'}
                >
                  {showArchived ? <BsArchiveFill size={16} /> : <BsArchive size={16} />}
                </button>
                <CreateChannel
                  onClick={() => {
                    setParam('channel', null)
                    setParam('create', 'true')
                  }}
                />
              </div>
            </div>
            <div className="flex-1 min-h-0">
              <ErrorBoundary
                fallback={<div className="text-red-400 text-sm p-2">Failed to load channels</div>}
              >
                <ChannelList
                  selected={selectedChannel}
                  onSelect={(name) => {
                    setParam('create', null)
                    setParam('channel', name)
                  }}
                  showArchived={showArchived}
                  isCreating={false}
                  onCreateChannel={() => {}}
                  onCancelCreate={() => {}}
                />
              </ErrorBoundary>
            </div>
          </div>
        </Panel>

        <div
          className={`md:hidden fixed top-0 left-0 bottom-0 w-80 bg-neutral-900 border-r border-neutral-800 z-50 transform transition-transform ${showChannelDrawer ? 'translate-x-0' : '-translate-x-full'}`}
        >
          <div className="h-full p-4 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
                Channels
              </h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setParam('archived', showArchived ? null : 'true')}
                  className={`p-1.5 rounded transition-colors ${
                    showArchived
                      ? 'text-cyan-400 hover:text-cyan-300'
                      : 'text-neutral-500 hover:text-neutral-400'
                  }`}
                  title={showArchived ? 'Show active channels' : 'Show archived channels'}
                >
                  {showArchived ? <BsArchiveFill size={16} /> : <BsArchive size={16} />}
                </button>
                <CreateChannel
                  onClick={() => {
                    setParam('channel', null)
                    setParam('create', 'true')
                    setShowChannelDrawer(false)
                  }}
                />
              </div>
            </div>
            <div className="flex-1 min-h-0">
              <ErrorBoundary
                fallback={<div className="text-red-400 text-sm p-2">Failed to load channels</div>}
              >
                <ChannelList
                  selected={selectedChannel}
                  onSelect={(name) => {
                    setParam('create', null)
                    setParam('channel', name)
                    setShowChannelDrawer(false)
                  }}
                  showArchived={showArchived}
                  isCreating={false}
                  onCreateChannel={() => {}}
                  onCancelCreate={() => {}}
                />
              </ErrorBoundary>
            </div>
          </div>
        </div>

        <PanelResizeHandle className="hidden md:block w-1 bg-neutral-800 hover:bg-neutral-700 transition-colors" />

        <Panel defaultSize={42} minSize={25}>
          <div className="h-full flex flex-col md:p-4" style={{ height: '100%' }}>
            {isCreating && (
              <div className="hidden md:block">
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
                    timer_expires_at: null,
                    timer_set_by_message_id: null,
                  }}
                  isCreating={true}
                  onCreate={(name, topic) => createChannel({ name, topic })}
                  onCancelCreate={() => setParam('create', null)}
                  createError={createError}
                />
              </div>
            )}
            {currentChannel ? (
              <ErrorBoundary
                fallback={<div className="text-red-400 text-sm">Failed to load channel</div>}
              >
                <div className="hidden md:block">
                  <ChannelHeader channel={currentChannel} onExportClick={handleExportChannel} />
                </div>
                <div className="flex-1 overflow-y-auto scrollable min-h-0 px-4 md:px-0">
                  <MessageList
                    channelName={currentChannel.name}
                    channelId={currentChannel.channel_id}
                  />
                </div>

                <div className="shrink-0">
                  {agentTabs.length > 0 && (
                    <div className="border-t border-neutral-800 overflow-x-auto flex gap-2 px-4 py-2 md:hidden">
                      {agentTabs.map((tab) => (
                        <button
                          key={tab.agentId}
                          onClick={() => {
                            setParam('agent', tab.agentId)
                            setShowSessionModal(true)
                          }}
                          className="px-3 py-1.5 rounded-full text-xs flex items-center gap-2 whitespace-nowrap border transition-colors shrink-0 bg-neutral-800 border-neutral-700 text-neutral-300 hover:border-cyan-500 hover:text-white"
                        >
                          {tab.identity ?? tab.agentId.slice(0, 8)}
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              tab.isRunning ? 'bg-green-400' : 'bg-neutral-600'
                            }`}
                          />
                        </button>
                      ))}
                    </div>
                  )}

                  <AgentStatus channel={currentChannel.name} />
                  <div
                    className="px-4 md:px-0"
                    style={{ paddingBottom: 'max(env(safe-area-inset-bottom), 1rem)' }}
                  >
                    <ComposeBox channel={currentChannel.name} />
                  </div>
                </div>
              </ErrorBoundary>
            ) : null}
          </div>
        </Panel>

        <PanelResizeHandle className="hidden md:block w-1 bg-neutral-800 hover:bg-neutral-700 transition-colors" />

        <Panel defaultSize={43} minSize={25} className="hidden md:block">
          <div className="h-full border-l border-neutral-800 flex flex-col">
            {agentTabs.length > 0 ? (
              <>
                <div className="flex border-b border-neutral-800 overflow-x-auto">
                  {agentTabs.map((tab) => (
                    <button
                      key={tab.agentId}
                      onClick={() => setParam('agent', tab.agentId)}
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
                  {selectedTab?.sessionId && <ContextIndicator sessionId={selectedTab.sessionId} />}
                  <ErrorBoundary
                    fallback={<div className="text-red-400 text-sm">Failed to load session</div>}
                  >
                    {selectedTab?.sessionId ? (
                      <SessionStream sessionId={selectedTab.sessionId} />
                    ) : (
                      <div className="text-neutral-500 text-sm">Waiting for session...</div>
                    )}
                  </ErrorBoundary>
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
