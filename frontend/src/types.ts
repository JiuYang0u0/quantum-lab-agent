export type Limits = {max_steps:number;max_tools:number;seconds:number}
export type Config = {profile:string;model:string;max_tokens:number;fixture:boolean;defaults:Limits;bounds:Limits}
export type Event = {seq:number;created:number;kind:string;data:Record<string, any>}
export type Run = {run_id:string;family:string;prompt:string;status:string;created:number;events:Event[];grounded_output:string}
export const active = (status:string) => ['running','queued'].includes(status)
export async function get<T>(url:string):Promise<T> {
  const response = await fetch(url)
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}
