"use client"

import { useEffect } from "react"

/**
 * Suppresses React hydration warnings caused by browser extensions
 * (e.g., Bitdefender, uBlock, etc.) that inject attributes like
 * `bis_skin_checked="1"` into DOM nodes before React can hydrate.
 *
 * This is a dev-only cosmetic overlay issue — it does NOT affect
 * runtime behavior or production builds.
 */
export function HydrationSuppressor() {
  useEffect(() => {
    const originalError = console.error

    console.error = (...args: any[]) => {
      const msg = typeof args[0] === "string" ? args[0] : ""
      
      // Suppress hydration warnings caused by browser extension attribute injection
      if (
        msg.includes("bis_skin_checked") ||
        msg.includes("A tree hydrated but some attributes") ||
        (msg.includes("did not match") && args.some((a: any) => 
          typeof a === "string" && a.includes("bis_skin_checked")
        ))
      ) {
        return
      }

      originalError.apply(console, args)
    }

    return () => {
      console.error = originalError
    }
  }, [])

  return null
}
