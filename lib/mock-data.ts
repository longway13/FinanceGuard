import type { RiskScore, DisputeCase } from "@/lib/types"

// Mock risk scores
const riskScores: RiskScore[] = [
  {
    category: "Legal Compliance",
    score: 35,
    description: "Some potential compliance issues with recent regulatory changes.",
  },
  {
    category: "Fee Structure",
    score: 65,
    description: "Higher than average fees with complex calculation methods.",
  },
  {
    category: "Liquidity Risk",
    score: 80,
    description: "Significant restrictions on withdrawals and redemptions.",
  },
  {
    category: "Market Risk",
    score: 55,
    description: "Moderate exposure to market volatility and economic downturns.",
  },
  {
    category: "Transparency",
    score: 40,
    description: "Some key information is not clearly disclosed or is difficult to understand.",
  },
]

// Mock dispute cases
const disputeCases: DisputeCase[] = [
  {
    id: "DC-2023-1045",
    title: "Smith v. Financial Products Corp",
    status: "Resolved",
    date: "Mar 15, 2023",
    jurisdiction: "Federal Court",
    summary:
      "Investor claimed that fee structure was misrepresented in the product documentation, leading to unexpected charges.",
    keyIssues: ["Misleading fee disclosure", "Inadequate risk warnings", "Failure to disclose conflicts of interest"],
    outcome: "Settled for $1.2M with agreement to revise disclosure documents.",
    relevance: "This case involved similar fee structure language to what appears in your document on page 24.",
  },
  {
    id: "DC-2022-0872",
    title: "Johnson Retirement Fund v. Investment Advisors Inc",
    status: "Ongoing",
    date: "Nov 8, 2022",
    jurisdiction: "State Court",
    summary:
      "Class action regarding hidden fees and charges that were not properly disclosed in the investment prospectus.",
    keyIssues: [
      "Hidden fees not disclosed in main documentation",
      "Misleading performance projections",
      "Inadequate risk disclosure",
    ],
    outcome: "Case is ongoing with preliminary injunction granted to plaintiffs.",
    relevance: "The dispute centers on similar liquidity restriction clauses found in your document section 5.3.",
  },
  {
    id: "DC-2022-0651",
    title: "Garcia v. Global Investment Partners",
    status: "Resolved",
    date: "Jul 22, 2022",
    jurisdiction: "Arbitration",
    summary:
      "Investor disputed the risk classification of the product, claiming it was marketed as lower risk than actual performance indicated.",
    keyIssues: [
      "Misclassification of risk level",
      "Aggressive marketing to unsuitable investors",
      "Failure to conduct proper suitability assessment",
    ],
    outcome: "Arbitrator ruled in favor of the investor, awarding $350,000 in damages.",
    relevance: "The risk classification methodology in this case is very similar to the one used in your document.",
  },
  {
    id: "DC-2021-1198",
    title: "Pension Trust v. Financial Services Group",
    status: "Resolved",
    date: "Dec 3, 2021",
    jurisdiction: "Federal Court",
    summary:
      "Institutional investor claimed that liquidity terms were substantially changed without proper notification.",
    keyIssues: [
      "Unilateral changes to redemption terms",
      "Inadequate notification of material changes",
      "Breach of fiduciary duty",
    ],
    outcome:
      "Court ruled in favor of defendant, finding that notification was adequate under the terms of the agreement.",
    relevance:
      "Your document contains similar language regarding the ability to change redemption terms with limited notice.",
  },
]

// Mock trend data
const trendData = [
  { month: "Jan", count: 12 },
  { month: "Feb", count: 15 },
  { month: "Mar", count: 18 },
  { month: "Apr", count: 14 },
  { month: "May", count: 21 },
  { month: "Jun", count: 25 },
  { month: "Jul", count: 30 },
  { month: "Aug", count: 28 },
  { month: "Sep", count: 32 },
  { month: "Oct", count: 35 },
  { month: "Nov", count: 38 },
  { month: "Dec", count: 42 },
]

// Mock document data
export const mockDocumentData = {
  overallRisk: 65,
  riskScores,
  keyFindings: [
    "The document contains complex fee structures with potential hidden charges.",
    "Liquidity restrictions are more severe than industry standard.",
    "Dispute resolution clause requires mandatory arbitration.",
    "Risk disclosures are present but scattered throughout the document.",
    "Early termination penalties are significantly higher than comparable products.",
  ],
  recommendations: [
    "Review section 4.3 carefully for fee structure details.",
    "Consider liquidity needs before committing to this product.",
    "Consult with a financial advisor about alternative products with better liquidity terms.",
    "Request clarification on specific risk factors mentioned on page 18.",
    "Compare early termination penalties with other similar products in the market.",
  ],
  disputeCases: {
    cases: disputeCases,
    totalCases: 24,
    trendData,
  },
}

