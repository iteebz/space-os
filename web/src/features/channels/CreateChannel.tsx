import { BsPlusCircle } from 'react-icons/bs'

interface Props {
  onClick: () => void
}

export function CreateChannel({ onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className="p-1.5 rounded transition-colors text-neutral-500 hover:text-neutral-400"
      title="Create new channel"
    >
      <BsPlusCircle size={16} />
    </button>
  )
}
