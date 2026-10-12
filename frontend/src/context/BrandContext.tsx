import React, { useState, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { BrandContext } from "./BrandContextDefinition";

export function BrandProvider({ children }: { children: React.ReactNode }) {
  const [selectedBrandId, setSelectedBrandId] = useState<string | null>(null);

  const { data: brandsData, isLoading: isLoadingBrands } = useQuery({
    queryKey: ["brands"],
    queryFn: () => apiClient.getBrands(),
  });

  const brands = useMemo(() => brandsData?.items || [], [brandsData?.items]);

  // Default to first brand (Kaveri Bank)
  useEffect(() => {
    if (brands.length > 0 && !selectedBrandId) {
      setSelectedBrandId(brands[0].id);
    }
  }, [brands, selectedBrandId]);

  const activeBrand = useMemo(() => {
    return brands.find((b) => b.id === selectedBrandId) || brands[0] || null;
  }, [brands, selectedBrandId]);

  // Query brand summary to get accurate findings and cleared counts for the nav
  const { data: summaryData } = useQuery({
    queryKey: ["brand-summary", activeBrand?.id],
    queryFn: () => (activeBrand ? apiClient.getBrandSummary(activeBrand.id) : null),
    enabled: !!activeBrand,
  });

  const findingsCount = summaryData?.funnel.findings ?? 12;
  const clearedCount =
    summaryData
      ? summaryData.funnel.official_cleared + summaryData.funnel.benign_lookalike
      : 19;

  return (
    <BrandContext.Provider
      value={{
        activeBrand,
        brands,
        setActiveBrandId: (id: string) => setSelectedBrandId(id),
        isLoading: isLoadingBrands,
        isDemoBrand: activeBrand?.demo_brand ?? true,
        findingsCount,
        clearedCount,
      }}
    >
      {children}
    </BrandContext.Provider>
  );
}
