import { useState } from 'react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import {
  ChannelList,
  MessageList,
  ComposeBox,
  ChannelAgents,
  CreateChannel,
  ChannelHeader,
  useChannels,
  useMessages,
} from './features/channels'
import { SessionList, SessionStream } from './features/sessions'
import { useAgents, useAgentMap } from './features/agents'
import { useSpawns } from './features/spawns'

type PanelView = 'agents' | 'sessions' | 'stream'

export default function App() {
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)
  const [showPanel, setShowPanel] = useState(false)
  const [panelView, setPanelView] = useState<PanelView>('agents')
  const [selectedAgentIdentity, setSelectedAgentIdentity] = useState<string | null>(null)
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const { data: channels } = useChannels()
  const { data: messages = [] } = useMessages(selectedChannel)
  const { data: agents } = useAgents()
  const { data: spawns } = useSpawns()
  const agentMap = useAgentMap()

  const currentChannel = channels?.find((c) => c.name === selectedChannel)

  const handleAgentClick = (agentIdentity: string) => {
    const agent = agents?.find((a) => a.identity === agentIdentity)
    if (!agent) return

    setSelectedAgentIdentity(agentIdentity)

    const agentSpawns = spawns
      ?.filter((s) => s.agent_id === agent.agent_id && s.session_id)
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

    const runningSpawn = agentSpawns?.find(
      (s) => s.status === 'running' && s.channel_id === currentChannel?.channel_id
    )

    if (runningSpawn?.session_id) {
      setSelectedSessionId(runningSpawn.session_id)
      setPanelView('stream')
    } else if (agentSpawns && agentSpawns.length > 0 && agentSpawns[0].session_id) {
      setSelectedSessionId(agentSpawns[0].session_id)
      setPanelView('stream')
    } else {
      setPanelView('sessions')
    }
  }

  const handleSessionClick = (sessionId: string) => {
    setSelectedSessionId(sessionId)
    setPanelView('stream')
  }

  const handleShowAllSessions = () => {
    setPanelView('sessions')
  }

  const handleBack = () => {
    if (panelView === 'stream') {
      setPanelView('sessions')
      setSelectedSessionId(null)
    } else if (panelView === 'sessions') {
      setPanelView('agents')
      setSelectedAgentIdentity(null)
    }
  }

  const selectedAgent = agents?.find((a) => a.identity === selectedAgentIdentity)
  const selectedAgentSpawn = spawns?.find(
    (s) =>
      s.agent_id === selectedAgent?.agent_id &&
      s.channel_id === currentChannel?.channel_id &&
      s.status === 'running'
  )

  const getPanelTitle = () => {
    if (panelView === 'stream' && selectedAgentIdentity) {
      return selectedAgentIdentity
    }
    if (panelView === 'sessions') {
      return 'Sessions'
    }
    return 'Agents'
  }

  const handleExportChannel = () => {
    if (!messages.length) return

    const text = messages
      .map((msg) => {
        const identity = agentMap.get(msg.agent_id) ?? msg.agent_id.slice(0, 7)
        const isoString = msg.created_at.endsWith('Z') ? msg.created_at : `${msg.created_at}Z`
        const timestamp = new Date(isoString).toLocaleString()
        return `[${timestamp}] ${identity}:\n${msg.content}\n`
      })
      .join('\n')

    void navigator.clipboard.writeText(text).then(() => {})
  }

  return (
    <div className="h-screen w-screen">
      <PanelGroup direction="horizontal">
        <Panel defaultSize={20} minSize={15}>
          <div className="h-full border-r border-neutral-800 p-4">
            <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide mb-4">
              Channels
            </h2>
            <CreateChannel onChannelCreated={setSelectedChannel} />
            <ChannelList selected={selectedChannel} onSelect={setSelectedChannel} />
          </div>
        </Panel>

        <PanelResizeHandle className="w-1 bg-neutral-800 hover:bg-neutral-700 transition-colors" />

        <Panel defaultSize={50}>
          <div className="h-full p-4 flex flex-col">
            {selectedChannel && currentChannel ? (
              <>
                <ChannelHeader
                  channel={currentChannel}
                  onInfoClick={() => setShowPanel(!showPanel)}
                  onExportClick={handleExportChannel}
                />
                <div className="flex-1 overflow-y-auto">
                  <MessageList channel={selectedChannel} />
                </div>
                <ComposeBox channel={selectedChannel} />
              </>
            ) : (
              <div className="text-neutral-500">Select a channel</div>
            )}
          </div>
        </Panel>

        {showPanel && (
          <>
            <PanelResizeHandle className="w-1 bg-neutral-800 hover:bg-neutral-700 transition-colors" />

            <Panel defaultSize={30} minSize={20}>
              <div className="h-full border-l border-neutral-800 p-4 flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide">
                    {getPanelTitle()}
                  </h2>
                  <div className="flex gap-2">
                    {panelView !== 'agents' && (
                      <button
                        onClick={handleBack}
                        className="text-neutral-500 hover:text-white text-sm"
                      >
                        back
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setShowPanel(false)
                        setPanelView('agents')
                        setSelectedAgentIdentity(null)
                        setSelectedSessionId(null)
                      }}
                      className="text-neutral-500 hover:text-white"
                    >
                      ×
                    </button>
                  </div>
                </div>

                {panelView === 'stream' && selectedSessionId ? (
                  <div className="flex-1 flex flex-col min-h-0">
                    {selectedAgent && (
                      <div className="mb-3 pb-3 border-b border-neutral-800 flex-shrink-0">
                        <div className="flex items-center gap-2">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              selectedAgentSpawn ? 'bg-green-400' : 'bg-neutral-600'
                            }`}
                          />
                          <span className="text-sm text-neutral-300">{selectedAgent.model}</span>
                        </div>
                        <button
                          onClick={handleShowAllSessions}
                          className="text-xs text-neutral-500 hover:text-neutral-300 mt-1"
                        >
                          All sessions →
                        </button>
                      </div>
                    )}
                    <div className="flex-1 overflow-y-auto">
                      <SessionStream sessionId={selectedSessionId} />
                    </div>
                  </div>
                ) : panelView === 'sessions' && selectedAgentIdentity ? (
                  <div className="flex-1 overflow-y-auto">
                    <SessionList
                      agentId={selectedAgentIdentity}
                      channelId={selectedChannel}
                      onSessionClick={handleSessionClick}
                    />
                  </div>
                ) : (
                  <div className="flex-1 overflow-y-auto">
                    {selectedChannel && (
                      <ChannelAgents channel={selectedChannel} onAgentClick={handleAgentClick} />
                    )}
                  </div>
                )}
              </div>
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  )
}
