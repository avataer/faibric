export interface Section {
  id: string
  type: string
  label: string
  html?: string
}

export type SectionAction = "add" | "remove" | "reorder" | "duplicate"

export interface SectionTypeDefinition {
  type: string
  label: string
  icon: string
  description: string
  category: string
}

export const SECTION_CATEGORIES = [
  "Header & Navigation",
  "Content",
  "Social Proof",
  "Conversion",
  "Footer & Info",
] as const

export type SectionCategory = (typeof SECTION_CATEGORIES)[number]

export const SECTION_TYPES: SectionTypeDefinition[] = [
  {
    type: "hero",
    label: "Hero",
    icon: "ViewQuilt",
    description: "Large banner section with headline, subtext, and call-to-action",
    category: "Header & Navigation",
  },
  {
    type: "features",
    label: "Features",
    icon: "Dashboard",
    description: "Grid or list of product features with icons",
    category: "Content",
  },
  {
    type: "pricing",
    label: "Pricing",
    icon: "AttachMoney",
    description: "Pricing plans displayed in cards or columns",
    category: "Conversion",
  },
  {
    type: "testimonials",
    label: "Testimonials",
    icon: "FormatQuote",
    description: "Customer reviews and quotes with avatars",
    category: "Social Proof",
  },
  {
    type: "contact",
    label: "Contact",
    icon: "ContactMail",
    description: "Contact form with fields and submit button",
    category: "Footer & Info",
  },
  {
    type: "footer",
    label: "Footer",
    icon: "ViewAgenda",
    description: "Page footer with links, copyright, and social icons",
    category: "Footer & Info",
  },
  {
    type: "gallery",
    label: "Gallery",
    icon: "PhotoLibrary",
    description: "Image gallery or portfolio grid",
    category: "Content",
  },
  {
    type: "cta",
    label: "Call to Action",
    icon: "Campaign",
    description: "Prominent call-to-action banner with button",
    category: "Conversion",
  },
  {
    type: "team",
    label: "Team",
    icon: "Group",
    description: "Team member cards with photos and bios",
    category: "Social Proof",
  },
  {
    type: "faq",
    label: "FAQ",
    icon: "QuestionAnswer",
    description: "Frequently asked questions in accordion format",
    category: "Footer & Info",
  },
]
