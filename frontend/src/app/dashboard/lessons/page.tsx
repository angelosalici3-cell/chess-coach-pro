"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Le lezioni ora vivono nella scheda Partite: i vecchi collegamenti arrivano comunque nel posto giusto. */
export default function LessonsRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/dashboard/games?tab=lessons"); }, [router]);
  return null;
}
