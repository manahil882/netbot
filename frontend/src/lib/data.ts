export type Role = "user" | "bot";

export type Source = {
  id: string;
  tag: string;
  title: string;
  blurb: string;
  meta: string;
  match: number;
};

export type Message = {
  id: string;
  role: Role;
  text: string;
  cite?: string;
  pending?: boolean;
};

export type Conversation = {
  id: string;
  title: string;
  group: string;
  subtitle: string;
  messages: Message[];
  sources: Source[];
};

export const USER = {
  name: "Manahil Asif",
  shortName: "Manahil",
  email: "manahil@netsol.com",
  initial: "M",
};

export const AVATAR_OPTIONS = [
  { id: "m", glyph: "M", background: "linear-gradient(135deg,#8FB8E8,#003876)", color: "white" },
  { id: "a", glyph: "A", background: "linear-gradient(135deg,#4A90E2,#001A3D)", color: "white" },
  { id: "n", glyph: "N", background: "linear-gradient(135deg,#6B7385,#1A1F2A)", color: "white" },
  { id: "half", glyph: "\u25D0", background: "linear-gradient(135deg,#8A93A6,#2B3241)", color: "white" },
  { id: "star", glyph: "\u2726", background: "linear-gradient(135deg,#0A5CB0,#14181F)", color: "white" },
  { id: "diamond", glyph: "\u25C7", background: "linear-gradient(135deg,#E6EEF7,#4A90E2)", color: "var(--navy)" },
];

const COMPLIANCE_SOURCES: Source[] = [
  {
    id: "sbp-cir",
    tag: "Circular",
    title: "SBP-CIR-2026-14",
    blurb:
      "Amendments to AML/CFT reporting thresholds and STR filing windows for scheduled banks.",
    meta: "p. 4 · aug 12",
    match: 98,
  },
  {
    id: "aml-manual",
    tag: "Policy",
    title: "NETSOL AML manual v3.2",
    blurb:
      "Internal procedures for suspicious transaction escalation, updated to reflect new SBP guidance.",
    meta: "§ 4.1 · sep 1",
    match: 84,
  },
  {
    id: "q2-board",
    tag: "Memo",
    title: "Q2 board note",
    blurb:
      "Prior-quarter compliance summary. Referenced for historical thresholds and context.",
    meta: "p. 2 · jun 30",
    match: 71,
  },
];

export const CONVERSATIONS: Conversation[] = [
  {
    id: "q3-compliance-memo",
    title: "Q3 Compliance memo",
    group: "Today",
    subtitle: "Grounded on 4 documents · updated 2m ago",
    sources: COMPLIANCE_SOURCES,
    messages: [
      {
        id: "m1",
        role: "user",
        text: "What did the SBP circular from August change for cross-border reporting?",
      },
      {
        id: "m2",
        role: "bot",
        text: "Two things changed. The reporting threshold dropped from $10,000 to $5,000, and STRs must now be filed within 3 working days instead of 7.",
        cite: "SBP-CIR-2026-14 · p.4",
      },
      {
        id: "m3",
        role: "user",
        text: "Draft a one-liner for the client memo.",
      },
      {
        id: "m4",
        role: "bot",
        text: "Effective August 2026, cross-border transactions above $5,000 require reporting, and suspicious transaction reports must be filed within 3 working days.",
        cite: "SBP-CIR-2026-14 · p.4",
      },
    ],
  },
  {
    id: "payroll-formula-check",
    title: "Payroll formula check",
    group: "Today",
    subtitle: "Grounded on 2 documents · updated 1h ago",
    sources: [
      {
        id: "payroll-spec",
        tag: "Spec",
        title: "Payroll engine v9 spec",
        blurb: "Gross-to-net calculation order, including tax slabs and provident fund handling.",
        meta: "§ 2.3 · jul 18",
        match: 93,
      },
      {
        id: "fbr-slabs",
        tag: "Reference",
        title: "FBR slab table 2026",
        blurb: "Current-year salaried income tax slabs used by the payroll engine.",
        meta: "p. 1 · jul 1",
        match: 88,
      },
    ],
    messages: [
      {
        id: "p1",
        role: "user",
        text: "Does the payroll engine apply provident fund before or after tax?",
      },
      {
        id: "p2",
        role: "bot",
        text: "Before. The engine subtracts the employee provident fund contribution from gross pay, then applies the FBR slab to the remainder.",
        cite: "Payroll engine v9 spec · § 2.3",
      },
    ],
  },
  {
    id: "onboarding-deck-outline",
    title: "Onboarding deck outline",
    group: "This week",
    subtitle: "Grounded on 3 documents · updated 2d ago",
    sources: [
      {
        id: "onboard-hb",
        tag: "Handbook",
        title: "New joiner handbook",
        blurb: "Week-one checklist, systems access, and buddy programme overview.",
        meta: "p. 6 · may 4",
        match: 90,
      },
    ],
    messages: [
      {
        id: "o1",
        role: "user",
        text: "Outline a 10-slide onboarding deck for new engineers.",
      },
      {
        id: "o2",
        role: "bot",
        text: "Start with welcome and org map, then environment setup, codebase tour, branching model, review culture, on-call basics, security training, the buddy programme, week-one goals, and a Q&A slide.",
        cite: "New joiner handbook · p.6",
      },
    ],
  },
  {
    id: "vendor-redlines",
    title: "Vendor redlines",
    group: "This week",
    subtitle: "Grounded on 5 documents · updated 3d ago",
    sources: [
      {
        id: "msa",
        tag: "Contract",
        title: "Vendor MSA draft 4",
        blurb: "Master services agreement with redlines on liability caps and data residency.",
        meta: "§ 11 · aug 2",
        match: 95,
      },
    ],
    messages: [
      {
        id: "v1",
        role: "user",
        text: "Summarise the open redlines on liability.",
      },
      {
        id: "v2",
        role: "bot",
        text: "The vendor wants liability capped at 6 months of fees; our counter is 12 months plus carve-outs for data breach and IP infringement. That clause is still open.",
        cite: "Vendor MSA draft 4 · § 11",
      },
    ],
  },
  {
    id: "iso-27001-gap-review",
    title: "ISO 27001 gap review",
    group: "This week",
    subtitle: "Grounded on 6 documents · updated 4d ago",
    sources: [
      {
        id: "iso-gap",
        tag: "Audit",
        title: "ISO 27001 gap analysis",
        blurb: "Control-by-control readiness assessment ahead of the certification audit.",
        meta: "p. 12 · aug 8",
        match: 97,
      },
    ],
    messages: [
      {
        id: "i1",
        role: "user",
        text: "Which Annex A controls are still failing?",
      },
      {
        id: "i2",
        role: "bot",
        text: "Three remain open: A.8.16 monitoring activities, A.5.7 threat intelligence, and A.8.28 secure coding. Everything else is either met or has a dated remediation plan.",
        cite: "ISO 27001 gap analysis · p.12",
      },
    ],
  },
  {
    id: "client-kickoff-notes",
    title: "Client kickoff notes",
    group: "This week",
    subtitle: "Grounded on 2 documents · updated 5d ago",
    sources: [
      {
        id: "kickoff",
        tag: "Notes",
        title: "Kickoff transcript",
        blurb: "Recorded kickoff call covering scope, milestones, and escalation contacts.",
        meta: "p. 3 · aug 6",
        match: 82,
      },
    ],
    messages: [
      {
        id: "k1",
        role: "user",
        text: "What did the client commit to on data migration?",
      },
      {
        id: "k2",
        role: "bot",
        text: "They agreed to deliver a full extract of legacy records by the end of month two, with a sample set in week three so mapping can start early.",
        cite: "Kickoff transcript · p.3",
      },
    ],
  },
];

/**
 * Stand-in for the RAG backend. Replaced by a real API call once the
 * retrieval service is wired up.
 */
export function draftAnswer(question: string, conversation: Conversation) {
  const top = conversation.sources[0];
  const trimmed = question.trim().replace(/\s+/g, " ");
  const topic = trimmed.length > 60 ? `${trimmed.slice(0, 57)}…` : trimmed;

  if (!top) {
    return {
      text: `I don't have any documents indexed for this chat yet. Attach a file or connect your knowledge base, then ask about "${topic}" again.`,
      cite: undefined,
    };
  }

  const sourceCount = conversation.sources.length;

  return {
    text: `Here is what the indexed documents say about "${topic}". ${sourceCount} source${
      sourceCount === 1 ? "" : "s"
    } matched, and ${top.title} is the closest at ${top.match}%. Connect the retrieval service to replace this placeholder with a grounded answer.`,
    cite: `${top.title} · ${top.meta.split(" · ")[0]}`,
  };
}

export const ENROLL_STEPS = [
  {
    id: "center",
    label: "Center",
    heading: ["Look straight", "at the camera."],
    copy: "Keep your face inside the frame. Well-lit, glasses off if you can.",
  },
  {
    id: "left",
    label: "Left",
    heading: ["Turn slowly", "to your left."],
    copy: "Keep your face inside the frame. Well-lit, glasses off if you can.",
  },
  {
    id: "right",
    label: "Right",
    heading: ["Now turn", "to your right."],
    copy: "Last one. Hold steady until the ring completes.",
  },
];
