/**
 * @file sectorHelpers.js
 * @description Helper functions for normalizing, filtering, sorting, and analyzing sector data.
 */

/**
 * Normalizes sector data from either the flat mock data structure
 * or the backend sector_industry_engine response contract.
 * 
 * @param {object} s - Raw sector object
 * @param {number} index - Index for fallback naming/ranking
 * @returns {object} Normalized sector model
 */
export function normalizeSectorData(s, index = 0) {
  if (!s || typeof s !== 'object') {
    return {
      id: `sector-${index + 1}`,
      name: `Sector ${index + 1}`,
      rank: index + 1,
      performance_21d: null,
      performance_63d: null,
      performance_126d: null,
      relativeStrength: null,
      relativeStrengthStatus: 'UNAVAILABLE',
      relativeStrengthType: 'ratio',
      status: 'In-line',
      statusBadgeClass: 'bg-accent-warning/10 text-accent-warning border-accent-warning/20',
      stockCount: null,
      constituentsList: null,
      score: null,
    };
  }

  const name = s.sector || s.sector_name || s.name || `Sector ${index + 1}`;

  // Multi-timeframe performance calculation
  let p21 = s.performance_21d != null ? Number(s.performance_21d) : null;
  let p63 = s.performance_63d != null ? Number(s.performance_63d) : null;
  let p126 = s.performance_126d != null ? Number(s.performance_126d) : null;

  if (s.performance && typeof s.performance === 'object') {
    if (p21 == null && s.performance['21D'] != null) {
      const v = Number(s.performance['21D']);
      p21 = Math.abs(v) <= 1.0 ? v * 100 : v;
    }
    if (p63 == null && s.performance['63D'] != null) {
      const v = Number(s.performance['63D']);
      p63 = Math.abs(v) <= 1.0 ? v * 100 : v;
    }
    if (p126 == null && s.performance['126D'] != null) {
      const v = Number(s.performance['126D']);
      p126 = Math.abs(v) <= 1.0 ? v * 100 : v;
    }
  } else if (p63 == null && s.performance != null && !isNaN(Number(s.performance))) {
    const v = Number(s.performance);
    p63 = Math.abs(v) <= 1.0 ? v * 100 : v;
  }

  // Relative strength parsing
  let rs = null;
  let rsStatus = 'UNAVAILABLE';
  let rsType = 'ratio';

  if (s.relative_strength_vs_nifty != null && !isNaN(Number(s.relative_strength_vs_nifty))) {
    rs = Number(s.relative_strength_vs_nifty);
    rsStatus = 'VALID';
    rsType = 'ratio';
  } else if (s.relative_strength && typeof s.relative_strength === 'object') {
    rsStatus = s.relative_strength.status || 'UNAVAILABLE';
    if (s.relative_strength['63D_rs'] != null) {
      rs = Number(s.relative_strength['63D_rs']);
      rsType = 'difference';
    } else if (s.relative_strength['21D_rs'] != null) {
      rs = Number(s.relative_strength['21D_rs']);
      rsType = 'difference';
    }
  }

  // Determine performance classification (Outperforming, In-line, Lagging)
  let status = 'In-line';
  let statusBadgeClass = 'bg-accent-warning/10 text-accent-warning border-accent-warning/20';

  if (rsStatus === 'VALID' && rs != null) {
    if (rsType === 'ratio') {
      if (rs >= 1.05) {
        status = 'Outperforming';
        statusBadgeClass = 'bg-accent-green/10 text-accent-green border-accent-green/20';
      } else if (rs <= 0.95) {
        status = 'Lagging';
        statusBadgeClass = 'bg-accent-red/10 text-accent-red border-accent-red/20';
      }
    } else {
      // Difference-based relative strength
      if (rs >= 0.02) {
        status = 'Outperforming';
        statusBadgeClass = 'bg-accent-green/10 text-accent-green border-accent-green/20';
      } else if (rs <= -0.02) {
        status = 'Lagging';
        statusBadgeClass = 'bg-accent-red/10 text-accent-red border-accent-red/20';
      }
    }
  } else if (p63 != null) {
    // Fallback classification purely based on 63D return if RS benchmark is unavailable
    if (p63 > 5.0) {
      status = 'Outperforming';
      statusBadgeClass = 'bg-accent-green/10 text-accent-green border-accent-green/20';
    } else if (p63 < 0) {
      status = 'Lagging';
      statusBadgeClass = 'bg-accent-red/10 text-accent-red border-accent-red/20';
    }
  }

  // Stock count
  const stockCount = s.stock_count ?? s.constituents_count ?? (Array.isArray(s.constituents) ? s.constituents.length : null);
  const constituentsList = Array.isArray(s.constituents) ? s.constituents : null;
  const score = s.preliminary_score?.score ?? s.score ?? null;

  return {
    id: name,
    name,
    rank: s.rank ?? (index + 1),
    performance_21d: p21,
    performance_63d: p63,
    performance_126d: p126,
    relativeStrength: rs,
    relativeStrengthStatus: rsStatus,
    relativeStrengthType: rsType,
    status,
    statusBadgeClass,
    stockCount,
    constituentsList,
    score,
  };
}

/**
 * Filters a list of normalized sectors by search query and status.
 */
export function filterSectors(sectors, { searchQuery = '', statusFilter = 'ALL', stocksBySector = {} } = {}) {
  if (!Array.isArray(sectors)) return [];

  let result = [...sectors];

  // Search query filter
  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase().trim();
    result = result.filter((s) => {
      if (s.name.toLowerCase().includes(q)) return true;
      const key = s.name.trim().toLowerCase();
      const constituents = stocksBySector[key] || [];
      return constituents.some(
        (st) =>
          st.symbol?.toLowerCase().includes(q) ||
          st.company_name?.toLowerCase().includes(q)
      );
    });
  }

  // Status / Performance filter
  if (statusFilter !== 'ALL') {
    result = result.filter((s) => s.status === statusFilter);
  }

  return result;
}

/**
 * Sorts a list of sectors by specified criteria.
 */
export function sortSectors(sectors, sortBy = 'performance-desc', timeframe = '63d') {
  if (!Array.isArray(sectors)) return [];

  const sorted = [...sectors];

  const getPerf = (sec) => {
    if (timeframe === '21d') return sec.performance_21d ?? -9999;
    if (timeframe === '126d') return sec.performance_126d ?? -9999;
    return sec.performance_63d ?? -9999;
  };

  sorted.sort((a, b) => {
    if (sortBy === 'performance-desc') return getPerf(b) - getPerf(a);
    if (sortBy === 'performance-asc') return getPerf(a) - getPerf(b);
    if (sortBy === 'name-asc') return a.name.localeCompare(b.name);
    if (sortBy === 'stocks-desc') return (b.stockCount || 0) - (a.stockCount || 0);
    return 0;
  });

  return sorted;
}

/**
 * Computes aggregate summary statistics for a collection of normalized sectors.
 */
export function calculateSectorSummary(sectors) {
  if (!Array.isArray(sectors) || sectors.length === 0) {
    return {
      total: 0,
      outperforming: 0,
      lagging: 0,
      inLine: 0,
      topSector: null,
      topReturn: -Infinity,
    };
  }

  const total = sectors.length;
  const outperforming = sectors.filter((s) => s.status === 'Outperforming').length;
  const lagging = sectors.filter((s) => s.status === 'Lagging').length;
  const inLine = sectors.filter((s) => s.status === 'In-line').length;

  let topSector = null;
  let topReturn = -Infinity;

  for (const s of sectors) {
    const perf = s.performance_63d ?? s.performance_21d;
    if (perf != null && perf > topReturn) {
      topReturn = perf;
      topSector = s;
    }
  }

  return { total, outperforming, lagging, inLine, topSector, topReturn };
}
