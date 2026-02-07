export type AudienceType = 
  | "young-professionals"
  | "young-families" 
  | "pre-retirees"
  | "retirees"
  | "custom";

export interface AudienceConfig {
  id: AudienceType;
  label: string;
  description: string;
  topics: string[];
}

export const AUDIENCES: AudienceConfig[] = [
  {
    id: "young-professionals",
    label: "Young Professionals",
    description: "Ages 22-35, building their financial foundation",
    topics: [
      "financial foundation",
      "saving strategies",
      "goal setting",
      "budgeting basics",
      "investing for beginners",
      "student loans",
      "emergency funds",
      "career growth",
    ],
  },
  {
    id: "young-families",
    label: "Young Families",
    description: "Ages 30-45, growing families with competing priorities",
    topics: [
      "life insurance",
      "building wealth",
      "family budgeting",
      "achieving financial goals",
      "college funding",
      "529 plans",
      "protecting your family",
      "work-life balance",
    ],
  },
  {
    id: "pre-retirees",
    label: "Pre-Retirees",
    description: "Ages 50-65, planning for retirement",
    topics: [
      "retirement planning",
      "estate planning",
      "gifting strategies",
      "tax optimization",
      "catch-up contributions",
      "social security timing",
      "healthcare planning",
      "downsizing",
    ],
  },
  {
    id: "retirees",
    label: "Retirees",
    description: "Ages 65+, enjoying and managing retirement",
    topics: [
      "retirement income",
      "legacy planning",
      "grandchild gifting",
      "required minimum distributions",
      "medicare",
      "long-term care",
      "estate preservation",
      "charitable giving",
    ],
  },
];

export interface UserSettings {
  postsPerBatch: number;
  batchCount: 1 | 2;
  schedules: BatchSchedule[];
  sourceWebsites: string[];
  audience: AudienceType;
  customTopics: string[]; // Only used when audience is "custom"
  writingStyle: string;
  postLength: "short" | "medium" | "long";
  emailAddress: string;
  aiInstructions: string; // Custom instructions for AI (e.g., "no emojis")
}

export interface BatchSchedule {
  id: string;
  date: string; // ISO date string
  time: string; // HH:MM format
  enabled: boolean;
}

export interface GeneratedPost {
  id: string;
  batchId: string;
  topic: string;
  content: string;
  createdAt: string;
  status: "draft" | "edited" | "used";
  editHistory: PostEdit[];
}

export interface PostEdit {
  timestamp: string;
  userMessage: string;
  newContent: string;
}

export interface Batch {
  id: string;
  scheduledFor: string;
  generatedAt: string | null;
  posts: GeneratedPost[];
  status: "scheduled" | "generating" | "complete" | "sent";
}

export const DEFAULT_SETTINGS: UserSettings = {
  postsPerBatch: 5,
  batchCount: 1,
  schedules: [],
  sourceWebsites: [],
  audience: "young-professionals",
  customTopics: [],
  writingStyle: "",
  postLength: "medium",
  emailAddress: "",
  aiInstructions: "",
};

// Helper to get topics for an audience
export function getTopicsForAudience(audience: AudienceType, customTopics: string[] = []): string[] {
  if (audience === "custom") {
    return customTopics;
  }
  const config = AUDIENCES.find(a => a.id === audience);
  return config?.topics || [];
}

export const AUDIENCE = "New York Life financial advisors";
