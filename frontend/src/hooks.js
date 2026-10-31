import { useCallback, useEffect, useState } from 'react'
import { api } from './api.js'

/** GET a path; re-fetches when the path changes or reload() is called. */
export function useApi(path) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let alive = true
    api
      .get(path)
      .then((data) => alive && setState({ data, error: null, loading: false }))
      .catch((error) => alive && setState({ data: null, error, loading: false }))
    return () => {
      alive = false
    }
  }, [path, tick])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { ...state, reload }
}
