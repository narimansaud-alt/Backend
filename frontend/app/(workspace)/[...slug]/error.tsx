"use client";
import { RefreshCw } from "lucide-react";
export default function RouteError({reset}:{error:Error;reset:()=>void}){return <div className="panel grid min-h-[400px] place-items-center p-8 text-center"><div><h2 className="text-base font-semibold">Не удалось открыть раздел</h2><p className="mt-2 text-sm text-[#747a73]">Другие разделы кабинета продолжают работать.</p><button className="secondary-button mt-5" onClick={reset}><RefreshCw size={15}/>Повторить</button></div></div>}
