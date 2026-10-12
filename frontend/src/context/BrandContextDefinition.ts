import { createContext } from "react";
import type { Schema } from "@/api/client";

export interface BrandContextType {
  activeBrand: Schema["Brand"] | null;
  brands: Schema["Brand"][];
  setActiveBrandId: (id: string) => void;
  isLoading: boolean;
  isDemoBrand: boolean;
  findingsCount: number;
  clearedCount: number;
}

export const BrandContext = createContext<BrandContextType | undefined>(undefined);
