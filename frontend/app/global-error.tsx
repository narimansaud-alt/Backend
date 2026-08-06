"use client";
import { useEffect } from "react";
import { AlertTriangle } from "lucide-react";
import { sanitizeError } from "@/utils/error-sanitizer";

export default function GlobalError({error,reset}:{error:Error&{digest?:string};reset:()=>void}){useEffect(()=>{sanitizeError(error)},[error]);return <html lang="ru"><body className="grid min-h-screen place-items-center bg-[#f4f5f3] p-6 font-sans text-[#20231f]"><div className="max-w-md rounded-lg border border-[#dfe2dc] bg-white p-7 text-center"><AlertTriangle className="mx-auto text-[#a85a2f]"/><h1 className="mt-4 text-lg font-semibold">Что-то пошло не так</h1><p className="mt-2 text-sm text-[#747a73]">Мы сохранили безопасную диагностику. Обновите экран — остальные данные не пострадали.</p><button onClick={reset} className="mt-5 rounded-md bg-[#18362c] px-4 py-2 text-sm font-medium text-white">Повторить</button></div></body></html>}
