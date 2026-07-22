# All patients / clinical narrative are SYNTHETIC demo chrome.
# Evaluator numbers on Assessment / Evaluation / Trust / Benchmark pages
# must come from frontend/src/lib/api.ts (GitHubBench-Delta facade) — not from
# the hardcoded evalMetrics / trustScore / benchmarkRuns below.

// All patients are SYNTHETIC. Data generated for demo purposes only.

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
};

export const patients: SyntheticPatient[] = [
  {
    id: "SYN-0417",
    name: "Margaret H.",
    age: 82,
    sex: "F",
    chiefComplaint: "Two falls in the past month, worsening fatigue",
    comorbidities: ["Hypertension", "Osteoarthritis", "Mild cognitive impairment"],
    medications: ["Amlodipine 5mg", "Atorvastatin 20mg", "Vitamin D 1000IU"],
    livingSituation: "Lives alone, daughter visits weekly",
    riskProfile: "High",
  },
  {
    id: "SYN-0418",
    name: "Robert K.",
    age: 76,
    sex: "M",
    chiefComplaint: "Unintentional weight loss (4 kg / 3 months)",
    comorbidities: ["Type 2 diabetes", "CKD stage 3"],
    medications: ["Metformin 1000mg", "Lisinopril 10mg"],
    livingSituation: "Lives with spouse",
    riskProfile: "Moderate",
  },
  {
    id: "SYN-0419",
    name: "Yuki T.",
    age: 88,
    sex: "F",
    chiefComplaint: "Forgetting medications, mild disorientation at night",
    comorbidities: ["Atrial fibrillation", "Osteoporosis"],
    medications: ["Apixaban 5mg", "Alendronate weekly"],
    livingSituation: "Assisted living",
    riskProfile: "High",
  },
  {
    id: "SYN-0420",
    name: "Anton P.",
    age: 71,
    sex: "M",
    chiefComplaint: "Reduced walking distance, mild breathlessness",
    comorbidities: ["COPD", "Ex-smoker"],
    medications: ["Tiotropium inhaler", "Salbutamol PRN"],
    livingSituation: "Lives alone, independent",
    riskProfile: "Low",
  },
  {
    id: "SYN-0421",
    name: "Elena R.",
    age: 79,
    sex: "F",
    chiefComplaint: "Low mood, sleep disturbance since bereavement",
    comorbidities: ["Hypothyroidism"],
    medications: ["Levothyroxine 75mcg"],
    livingSituation: "Lives alone",
    riskProfile: "Moderate",
  },
];

export type Turn = { role: "clinician" | "patient" | "assistant"; text: string; t: string };

export const conversation: Turn[] = [
  { t: "00:00", role: "assistant", text: "Good morning Margaret. I'm the ElderWise assistant. Dr. Patel has asked me to help with a short check-in. Is that alright?" },
  { t: "00:08", role: "patient", text: "Yes, that's fine dear." },
  { t: "00:14", role: "assistant", text: "Thank you. Can you tell me about the two falls you had recently?" },
  { t: "00:20", role: "patient", text: "The first one was in the kitchen — I felt dizzy standing up. The second was on the stairs, my knee just gave way." },
  { t: "00:42", role: "assistant", text: "I'm sorry to hear that. Did you injure yourself?" },
  { t: "00:48", role: "patient", text: "A bruise on my hip, nothing broken." },
  { t: "01:01", role: "assistant", text: "How have you been managing at home since — cooking, bathing, getting to the shops?" },
  { t: "01:10", role: "patient", text: "Cooking is fine. Bathing I'm nervous now. I haven't been to the shops in two weeks." },
  { t: "01:32", role: "assistant", text: "That's helpful, thank you. How would you describe your energy day-to-day?" },
  { t: "01:38", role: "patient", text: "Tired. I nap in the afternoons which I never used to." },
  { t: "02:00", role: "assistant", text: "And your mood — has anything felt heavier than usual lately?" },
  { t: "02:07", role: "patient", text: "A little low, I suppose. I miss going out." },
  { t: "02:30", role: "clinician", text: "[Dr. Patel joins] Margaret, we'll run through a short memory check next." },
];

export type AssessmentDomain = {
  domain: string;
  score: number;
  max: number;
  flag: "normal" | "watch" | "concern";
  note: string;
};

export const assessment: AssessmentDomain[] = [
  { domain: "Mobility & Falls", score: 2, max: 5, flag: "concern", note: "≥2 falls in 12 months; postural symptoms." },
  { domain: "Nutrition", score: 4, max: 5, flag: "normal", note: "Stable weight, adequate intake reported." },
  { domain: "Cognition", score: 3, max: 5, flag: "watch", note: "Mild subjective forgetfulness; formal testing pending." },
  { domain: "Mood", score: 3, max: 5, flag: "watch", note: "Low mood post-bereavement; PHQ-2 positive." },
  { domain: "ADLs / IADLs", score: 3, max: 5, flag: "watch", note: "Reduced community access; bathing avoidance." },
  { domain: "Polypharmacy", score: 4, max: 5, flag: "normal", note: "3 regular medications; no anticholinergic burden." },
  { domain: "Social Support", score: 3, max: 5, flag: "watch", note: "Lives alone; weekly family contact." },
];

export type EvalMetric = {
  key: string;
  label: string;
  value: number;
  target: number;
  unit: "%" | "score";
  description: string;
};

// Metrics reflect GitHubBench-Delta evaluator outputs.
export const evalMetrics: EvalMetric[] = [
  { key: "faithfulness", label: "Faithfulness to Transcript", value: 94.2, target: 90, unit: "%", description: "Assessment fields grounded in conversation evidence." },
  { key: "coverage", label: "Domain Coverage", value: 87.5, target: 85, unit: "%", description: "Required RGA domains addressed." },
  { key: "safety", label: "Safety Flag Recall", value: 91.0, target: 95, unit: "%", description: "Detected fall-risk & red-flag mentions." },
  { key: "calibration", label: "Score Calibration", value: 88.6, target: 85, unit: "%", description: "Agreement with clinician-adjudicated scoring." },
  { key: "hallucination", label: "Hallucination Rate", value: 2.1, target: 5, unit: "%", description: "Unsupported claims in structured output (lower is better)." },
  { key: "toneEmpathy", label: "Tone & Empathy", value: 4.4, target: 4.0, unit: "score", description: "Rated 1–5 by adjudicator rubric." },
];

export const trustScore = {
  overall: 86,
  band: "Trusted with clinician oversight",
  breakdown: [
    { name: "Evidence Grounding", value: 92 },
    { name: "Clinical Coverage", value: 88 },
    { name: "Safety Sensitivity", value: 84 },
    { name: "Consistency (n=25 runs)", value: 81 },
    { name: "Reasoning Transparency", value: 85 },
  ],
};

/** @deprecated Demo-only. Prefer POST /evaluate and POST /trust via lib/api. */
export const benchmarkRuns = [
  { model: "ElderWise v0.4 (this run)", trust: 86, faith: 94, cover: 88, safety: 91 },
  { model: "ElderWise v0.3", trust: 79, faith: 89, cover: 84, safety: 85 },
  { model: "Generic Clinical LLM (baseline)", trust: 61, faith: 74, cover: 66, safety: 58 },
  { model: "Open-source 8B (baseline)", trust: 48, faith: 63, cover: 55, safety: 44 },
];

/** Demo timeline — narrative only, not live evaluator timing. */
export const timeline = [
  { t: "T+0.0s", label: "Synthetic patient loaded", detail: "SYN-0417 · Margaret H., 82F" },
  { t: "T+1.2s", label: "Conversation streamed", detail: "13 turns · 2m 41s clinical dialog" },
  { t: "T+3.8s", label: "LLM output generated", detail: "Structured RGA JSON returned" },
  { t: "T+4.1s", label: "GitHubBench-Delta evaluator", detail: "6 metrics computed on transcript ↔ output" },
  { t: "T+4.4s", label: "TrustScore composed", detail: "Weighted composite: 86 / 100" },
  { t: "T+4.6s", label: "Clinical summary drafted", detail: "Ready for clinician review" },
];

export const insights = [
  {
    title: "Empathy correlates with coverage",
    body: "Runs scoring ≥4.2 on Tone & Empathy showed +6.1 pts on Domain Coverage — patients disclosed ADL detail more freely.",
  },
  {
    title: "Safety recall lags on nocturnal symptoms",
    body: "Across n=120 synthetic runs, evaluator flagged 9% under-detection of nighttime disorientation cues.",
  },
  {
    title: "Bereavement context stabilises mood scoring",
    body: "Prompt variant B (life-context probe) reduced mood-domain variance by 34% without inflating false positives.",
  },
  {
    title: "Consistency ceiling at repeated runs",
    body: "Test-retest agreement plateaus near 0.83 κ; residual variance driven by open-ended IADL probes.",
  },
];
