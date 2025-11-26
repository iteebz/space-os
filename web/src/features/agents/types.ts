export interface Agent {
  agent_id: string
  identity: string
  model: string | null
  constitution: string | null
  role: string | null
  spawn_count: number
  created_at: string | null
  last_active_at: string | null
  archived_at: string | null
}

export interface Memory {
  memory_id: string
  agent_id: string
  message: string
  topic: string
  created_at: string
  archived_at: string | null
  core: boolean
  source: string
}
