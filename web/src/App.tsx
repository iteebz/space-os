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
} from './features/channels'
import { SessionList, SessionStream } from './features/sessions'

export default function App() {
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)
  const [showPanel, setShowPanel] = useState(false)
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const { data: channels } = useChannels()

  const handleAgentClick = (agentId: string) => {
    setSelectedAgentId(agentId)
    setSelectedSessionId(null)
  }

  const handleSessionClick = (sessionId: string) => {
    setSelectedSessionId(sessionId)
  }

  const handleBack = () => {
    if (selectedSessionId) {
      setSelectedSessionId(null)
    } else if (selectedAgentId) {
      setSelectedAgentId(null)
    }
  }

  const getPanelTitle = () => {
    if (selectedSessionId) return 'Stream'
    if (selectedAgentId) return 'Sessions'
    return 'Agents'
  }

  const channel = channels?.find((c) => c.name === selectedChannel)

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
                <ChannelHeader channel={channel} onInfoClick={() => setShowPanel(!showPanel)} />
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
                    {(selectedAgentId || selectedSessionId) && (
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
                        setSelectedAgentId(null)
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
                  ) : selectedAgentId ? (
                    <SessionList agentId={selectedAgentId} onSessionClick={handleSessionClick} />
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
