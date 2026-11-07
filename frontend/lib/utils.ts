import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Combines multiple Tailwind CSS class names safely using clsx and twMerge.
 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Format numbers with comma separators (e.g. 18420 -> 18,420).
 */
export function formatNumber(num: number): string {
  return new Intl.NumberFormat("en-US").format(num);
}
