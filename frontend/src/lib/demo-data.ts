// Synthetic patient chrome helpers. Fixed fixtures under datasets/synthetic/
// are the reproducible demo source. Evaluator numbers must come from
// frontend/src/lib/api.ts — never from hardcoded demo scores.

export type ScenarioType =
  | "complete"
  | "missing_finding"
  | "hallucination_risk"
  | "contraindication"
  | "incomplete";

export type SyntheticPatient = {
  id: string;
  name: string;
  age: number;
  sex: "F" | "M";
  chiefComplaint: string;
  comorbidities: string[];
  medications: string[];
  livingSituation: string;
  riskProfile: "Low" | "Moderate" | "High";
  scenarioType?: ScenarioType;
  /** When set (fixture patients), used instead of the templated chrome conversation. */
  conversation?: Turn[];
  conversationText?: string;
};

export type Turn = { role: "clinician" | "patient" | "assistant"; text: string; t: string };

const baseConversation: Turn[] = [
  {
    t: "00:00",
    role: "assistant",
    text: "Good morning {name}. I'm the ElderWise assistant. Dr. Patel has asked me to help with a short check-in. Is that alright?",
  },
  { t: "00:08", role: "patient", text: "Yes, that's fine dear." },
  {
    t: "00:14",
    role: "assistant",
    text: "Thank you. Can you tell me more about: {complaint}?",
  },
  {
    t: "00:20",
    role: "patient",
    text: "It's been bothering me. {complaint}. Living situation: {living}.",
  },
  {
    t: "00:42",
    role: "assistant",
    text: "I'm sorry to hear that. How have you been managing day to day?",
  },
  {
    t: "00:48",
    role: "patient",
    text: "Medications include {meds}. I try to keep up, but some days are harder.",
  },
  {
    t: "01:01",
    role: "assistant",
    text: "That's helpful, thank you. Any other conditions I should know about?",
  },
  { t: "01:10", role: "patient", text: "I have {comorbidities}." },
  {
    t: "01:32",
    role: "assistant",
    text: "How would you describe your energy and mood recently?",
  },
  {
    t: "01:38",
    role: "patient",
    text: "It varies. Risk feels {risk} to me, if that makes sense.",
  },
  {
    t: "02:00",
    role: "assistant",
    text: "Thank you — that gives us a clear picture for the structured assessment.",
  },
  { t: "02:07", role: "patient", text: "Alright. I appreciate you taking the time." },
  {
    t: "02:30",
    role: "clinician",
    text: "[Dr. Patel joins] We'll review the framework evaluation outputs next — patient narrative is synthetic; scores are live.",
  },
];

function normalizeTurnRole(role: string | undefined): Turn["role"] {
  if (role === "clinician" || role === "assistant" || role === "patient") return role;
  return "assistant";
}

/** Prefer fixture conversation turns; else templated chrome transcript. */
export function getConversation(patient: SyntheticPatient): Turn[] {
  if (patient.conversation && patient.conversation.length > 0) {
    return patient.conversation.map((t, i) => ({
      role: normalizeTurnRole(t.role),
      text: t.text,
      t: t.t || `00:${String(i * 10).padStart(2, "0")}`,
    }));
  }
  const first = patient.name.split(" ")[0] || patient.name;
  const replace = (text: string) =>
    text
      .replaceAll("{name}", first)
      .replaceAll("{complaint}", patient.chiefComplaint)
      .replaceAll("{living}", patient.livingSituation)
      .replaceAll("{meds}", patient.medications.join(", ") || "none listed")
      .replaceAll(
        "{comorbidities}",
        patient.comorbidities.join(", ") || "no other conditions listed",
      )
      .replaceAll("{risk}", patient.riskProfile.toLowerCase());

  return baseConversation.map((t) => ({ ...t, text: replace(t.text) }));
}
