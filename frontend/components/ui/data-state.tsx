import Link from "next/link";
import { AlertTriangle, LockKeyhole, RefreshCw, WifiOff } from "lucide-react";

export function DataError({ message, requestId, status }: { message: string; requestId?: string; status?: number }) {
  const forbidden = status === 403; const offline = status === 0;
  const Icon = forbidden ? LockKeyhole : offline ? WifiOff : AlertTriangle;
  return <div className="panel grid min-h-[360px] place-items-center p-8 text-center"><div className="max-w-md"><span className="mx-auto grid size-11 place-items-center rounded-full bg-[#f4ece1] text-[#9b5d28]"><Icon size={21} /></span><h2 className="mt-4 text-base font-semibold">{forbidden ? "Нет доступа" : offline ? "Нет подключения" : "Данные пока недоступны"}</h2><p className="mt-2 text-sm leading-6 text-[#747a73]">{message}</p>{requestId && <p className="mt-2 font-mono text-[10px] text-[#9ba09a]">Запрос: {requestId}</p>}<Link href="/dashboard" className="secondary-button mt-5"><RefreshCw size={15} />Повторить</Link></div></div>;
}
