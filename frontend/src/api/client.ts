import type { Digest } from '../types'

const BASE_URL = '/api'

export interface PipelineStatus {
  state: 'idle' | 'running' | 'complete' | 'failed'
  stage: string
  batch_id: string
  progress: {
    total: number
    succeeded: number
    processing: number
    errored: number
  }
  stats: Record<string, number>
  error: string | null
}

export async function getDigest(
  personaId: string,
  phaseOverride?: string,
  date?: string,
): Promise<Digest> {
  const params = new URLSearchParams()
  if (phaseOverride) {
    params.set('phase_override', phaseOverride)
  }
  if (date) {
    params.set('date', date)
  }
  const query = params.toString() ? `?${params.toString()}` : ''
  const response = await fetch(`${BASE_URL}/digest/${personaId}${query}`)
  if (!response.ok) {
    throw new Error(`Failed to fetch digest: ${response.statusText}`)
  }
  return response.json()
}

export async function runPipeline(fresh: boolean = true): Promise<{ status: string }> {
  const url = fresh ? `${BASE_URL}/pipeline/run?fresh=true` : `${BASE_URL}/pipeline/run`
  const response = await fetch(url, { method: 'POST' })
  if (!response.ok) {
    throw new Error(`Failed to run pipeline: ${response.statusText}`)
  }
  return response.json()
}

export async function getPipelineStatus(): Promise<PipelineStatus> {
  const response = await fetch(`${BASE_URL}/pipeline/status`)
  if (!response.ok) {
    throw new Error(`Failed to fetch pipeline status: ${response.statusText}`)
  }
  return response.json()
}

export async function getDigestDates(): Promise<string[]> {
  const response = await fetch(`${BASE_URL}/digest/dates`)
  if (!response.ok) {
    throw new Error(`Failed to fetch digest dates: ${response.statusText}`)
  }
  return response.json()
}

export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch(`${BASE_URL}/health`)
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.statusText}`)
  }
  return response.json()
}
