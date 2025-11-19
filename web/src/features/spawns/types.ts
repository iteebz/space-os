export interface Spawn {
  id: string
  agent_id: string
  status: string
  session_id: string | null
  channel_id: string | null
  created_at: string
  ended_at: string | null
}
