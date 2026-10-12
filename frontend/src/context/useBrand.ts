import { useContext } from "react";
import { BrandContext } from "./BrandContextDefinition";
import type { BrandContextType } from "./BrandContextDefinition";

export function useBrand(): BrandContextType {
  const context = useContext(BrandContext);
  if (!context) {
    throw new Error("useBrand must be used within a BrandProvider");
  }
  return context;
}
