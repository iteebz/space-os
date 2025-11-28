export interface Channel {
  channel_id?: string
  name: string
  topic: string | null
  message_count: number
  last_activity: string | null
  unread_count: number
  archived_at: string | null
  pinned_at: string | null
}

export interface Message {
  message_id: string
  channel_id: string
  agent_id: string
  content: string
  created_at: string
}
