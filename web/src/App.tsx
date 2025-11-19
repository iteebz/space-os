import { useState } from 'react'
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels'
import { ChannelList, MessageList, ComposeBox, ChannelAgents } from './features/channels'
import { SpawnList } from './features/spawns'

export default function App() {
  const [selectedChannel, setSelectedChannel] = useState<string | null>(null)
  const [selectedSpawn, setSelectedSpawn] = useState<string | null>(null)

  return (
    <div className="h-screen w-screen">
      <PanelGroup direction="horizontal">
        <Panel defaultSize={20} minSize={15}>
          <div className="h-full border-r border-neutral-800 p-4">
            <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide mb-4">
              Channels
            </h2>
            <ChannelList selected={selectedChannel} onSelect={setSelectedChannel} />
          </div>
        </Panel>

        <PanelResizeHandle className="w-1 bg-neutral-800 hover:bg-neutral-700 transition-colors" />

        <Panel defaultSize={50}>
          <div className="h-full p-4 flex flex-col">
            <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide mb-4">
              Messages
            </h2>
            {selectedChannel ? (
              <>
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

        <PanelResizeHandle className="w-1 bg-neutral-800 hover:bg-neutral-700 transition-colors" />

        <Panel defaultSize={30} minSize={20}>
          <div className="h-full border-l border-neutral-800 p-4">
            <h2 className="text-sm font-semibold text-neutral-400 uppercase tracking-wide mb-4">
              {selectedChannel ? `Agents` : 'All Spawns'}
            </h2>
            {selectedChannel ? (
              <ChannelAgents channel={selectedChannel} />
            ) : (
              <SpawnList selected={selectedSpawn} onSelect={setSelectedSpawn} />
            )}
          </div>
        </Panel>
      </PanelGroup>
    </div>
  )
}
