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
import { useAgentMap } from './features/agents'

export default function App() {
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)
  const [showPanel, setShowPanel] = useState(false)
  const [selectedAgentIdentity, setSelectedAgentIdentity] = useState<string | null>(null)
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const { data: channels } = useChannels()
  const { data: messages = [] } = useMessages(selectedChannel)
  const agentMap = useAgentMap()

  const handleAgentClick = (agentIdentity: string) => {
    // Find agent's most recent session from spawns
    const agent = agents?.find((a) => a.identity === agentIdentity)
    if (agent) {
      const agentSpawns = spawns
        ?.filter((s) => s.agent_id === agent.agent_id && s.session_id)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      
      if (agentSpawns && agentSpawns.length > 0) {
        // Open most recent session immediately
        setSelectedSessionId(agentSpawns[0].session_id)
        setSelectedAgentIdentity(agentIdentity)
        return
      }
    }
    
    // Fallback: show session list
    setSelectedAgentIdentity(agentIdentity)
    setSelectedSessionId(null)
  }

  const handleSessionClick = (sessionId: string) => {
    setSelectedSessionId(sessionId)
  }

  const handleBack = () => {
    if (selectedSessionId) {
      setSelectedSessionId(null)
    } else if (selectedAgentIdentity) {
      setSelectedAgentIdentity(null)
    }
  }

  const getPanelTitle = () => {
    if (selectedSessionId) return 'Stream'
    if (selectedAgentIdentity) return 'Sessions'
    return 'Agents'
  }

  const channel = channels?.find((c) => c.name === selectedChannel)

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

    void navigator.clipboard.writeText(text).then(() => {
      // Could add toast notification here
    })
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
            {selectedChannel && channel ? (
              <>
                <ChannelHeader
                  channel={channel}
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
                    {(selectedAgentIdentity || selectedSessionId) && (
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
                        setSelectedAgentIdentity(null)
                        setSelectedSessionId(null)
                      }}
                      className="text-neutral-500 hover:text-white"
                    >
                      ×
                    </button>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto">
                  {selectedSessionId ? (
                    <SessionStream sessionId={selectedSessionId} />
                  ) : selectedAgentIdentity ? (
                    <SessionList
                      agentId={selectedAgentIdentity}
                      channelId={selectedChannel}
                      onSessionClick={handleSessionClick}
                    />
                  ) : (
                    selectedChannel && (
                      <ChannelAgents channel={selectedChannel} onAgentClick={handleAgentClick} />
                    )
                  )}
                </div>
              </div>
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  )
}
