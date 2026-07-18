import { useEffect, useRef, useState } from 'react';
import type { SocketEvent } from '../types/websocket';
import { getWebSocketUrl } from '../config/runtime';

export function useWearableSocket(onEvent:(event:SocketEvent)=>void) {
  const [status,setStatus]=useState<'live'|'reconnecting'|'disconnected'>('disconnected');
  const callback=useRef(onEvent); callback.current=onEvent;
  useEffect(()=>{ let ws:WebSocket|undefined, cancelled=false, retry=0, timer:number|undefined;
    const connect=()=>{ if(cancelled)return; setStatus(retry?'reconnecting':'disconnected'); ws=new WebSocket(getWebSocketUrl());
      ws.onopen=()=>{retry=0;setStatus('live')}; ws.onmessage=(m)=>{try{callback.current(JSON.parse(m.data) as SocketEvent)}catch{console.warn('Ignoring invalid backend event')}};
      ws.onclose=()=>{if(!cancelled){setStatus('reconnecting'); timer=window.setTimeout(connect,Math.min(1000*2**retry++,10000))}}; ws.onerror=()=>ws?.close(); };
    connect(); return()=>{cancelled=true;if(timer)clearTimeout(timer);ws?.close()};
  },[]); return status;
}
