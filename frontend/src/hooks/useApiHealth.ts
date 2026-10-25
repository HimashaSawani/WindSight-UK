import { useQuery } from '@tanstack/react-query'
import { getHealth } from '../services/api'

export function useApiHealth() {
  return useQuery({ queryKey: ['health'], queryFn: getHealth, retry: 1 })
}
