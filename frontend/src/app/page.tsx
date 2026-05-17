"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import {
  Shield,
  Upload,
  FileText,
  Globe,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
  Scale,
  Brain,
  Eye,
  Languages,
  Loader2,
  Sparkles,
  Download,
} from "lucide-react";
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

// ============================================================
// TYPES
// ============================================================
interface ClauseVerdict {
  risk_score: number;
  risk_types: string[];
  verdict: string;
  plain_english: string;
  suggested_fix: string;
  real_world_impact: string;
  defense_validity: number | string;
  prosecution_validity: number | string;
}

interface Scenario {
  scenario_title: string;
  description: string;
  likelihood: string;
  financial_impact: string;
  outcome: string;
}

interface NegotiationAdvice {
  negotiation_strategy?: string;
  talking_points?: string[];
  acceptable_compromise?: string;
  walk_away_threshold?: string;
  alternative_clause?: string;
}

interface BenchmarkComparison {
  fair_example: string;
  red_flags: string[];
}

interface ClauseResult {
  clause: {
    clause_number: number;
    title: string;
    text: string;
    category: string;
  };
  defense: string;
  prosecution: string;
  verdict: ClauseVerdict;
  simple_explanation: string;
  scenarios?: Scenario[];
  negotiation_advice?: NegotiationAdvice;
  benchmark_comparison?: BenchmarkComparison;
  matched_patterns?: Array<{ pattern: string; risk: string; explanation: string }>;
}

interface Contradictions {
  contradictions?: Array<{ clause_a: string; clause_b: string; explanation: string }>;
  ambiguities?: Array<{ clause: string; ambiguous_term: string; possible_interpretations: string[] }>;
  missing_protections?: string[];
  unusual_terms?: Array<{ clause: string; why_unusual: string }>;
}

interface AnalysisResult {
  document_type: string;
  total_clauses: number;
  overall_risk_score: number;
  max_risk_score: number;
  risk_grade: string;
  recommendation: string;
  executive_summary: string;
  critical_issues: number;
  warnings_count: number;
  safe_count: number;
  clause_results: ClauseResult[];
  contradictions?: Contradictions;
  parsing_method: string;
  language_info: {
    original_language: string;
    was_translated: boolean;
  };
  nlp_sentiment: {
    score: number;
    magnitude: number;
    interpretation: string;
  };
  analysis_id: string;
}

// ============================================================
// RISK COLOR HELPERS
// ============================================================
function getRiskColor(score: number): string {
  if (score >= 8) return "text-red-500";
  if (score >= 5) return "text-yellow-500";
  return "text-green-500";
}

function getRiskBg(score: number): string {
  if (score >= 8) return "bg-red-500/20 border-red-500/50";
  if (score >= 5) return "bg-yellow-500/20 border-yellow-500/50";
  return "bg-green-500/20 border-green-500/50";
}

function getRiskBadge(score: number): string {
  if (score >= 8) return "bg-red-600";
  if (score >= 5) return "bg-yellow-600";
  return "bg-green-600";
}

function getGradeColor(grade: string): string {
  if (grade === "F" || grade === "D") return "text-red-500";
  if (grade === "C") return "text-yellow-500";
  return "text-green-500";
}

// ============================================================
// CLAUSE CARD COMPONENT
// ============================================================
function ClauseCard({ result, index }: { result: ClauseResult; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const verdict = result.verdict;
  const score = typeof verdict?.risk_score === "number" ? verdict.risk_score : 5;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className={`rounded-xl border p-5 mb-4 ${getRiskBg(score)} transition-all`}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(!expanded); } }}
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        aria-label={`Clause ${result.clause.clause_number}: ${result.clause.title}, Risk score ${score} out of 10. ${expanded ? 'Click to collapse' : 'Click to expand details'}`}
      >
        <div className="flex items-center gap-3">
          <span
            className={`text-xs font-bold px-2.5 py-1 rounded-full text-white ${getRiskBadge(score)}`}
          >
            {score}/10
          </span>
          <div>
            <h3 className="font-semibold text-white">
              {result.clause.clause_number}. {result.clause.title}
            </h3>
            <span className="text-xs text-gray-400 uppercase tracking-wide">
              {result.clause.category}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {verdict?.risk_types?.map((type: string, i: number) => (
            <span
              key={i}
              className="text-[10px] px-2 py-0.5 rounded bg-white/10 text-gray-300"
            >
              {type}
            </span>
          ))}
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>

      {/* Plain English Summary (always visible) */}
      <p className="text-sm text-gray-300 mt-3 leading-relaxed">
        {verdict?.plain_english || result.simple_explanation}
      </p>

      {/* Expanded Details */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mt-4 space-y-4">
              {/* Original Clause Text */}
              <div className="bg-black/30 rounded-lg p-4">
                <h4 className="text-xs uppercase tracking-wide text-gray-500 mb-2">
                  Original Clause Text
                </h4>
                <p className="text-sm text-gray-300 italic">&quot;{result.clause.text}&quot;</p>
              </div>

              {/* Adversarial Debate */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Defense */}
                <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Scale className="w-4 h-4 text-blue-400" />
                    <h4 className="text-sm font-semibold text-blue-400">
                      Corporate Lawyer (Defense)
                    </h4>
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-line">
                    {result.defense}
                  </p>
                </div>

                {/* Prosecution */}
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="w-4 h-4 text-red-400" />
                    <h4 className="text-sm font-semibold text-red-400">
                      Consumer Advocate (Prosecution)
                    </h4>
                  </div>
                  <p className="text-xs text-gray-300 leading-relaxed whitespace-pre-line">
                    {result.prosecution}
                  </p>
                </div>
              </div>

              {/* Judge Verdict */}
              <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-4 h-4 text-purple-400" />
                  <h4 className="text-sm font-semibold text-purple-400">
                    Judge&apos;s Verdict
                  </h4>
                </div>
                <p className="text-sm text-gray-300">{verdict?.verdict}</p>
              </div>

              {/* Real World Impact */}
              {verdict?.real_world_impact && (
                <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
                  <h4 className="text-xs uppercase tracking-wide text-orange-400 mb-1">
                    Real-World Impact
                  </h4>
                  <p className="text-sm text-gray-300">{verdict.real_world_impact}</p>
                </div>
              )}

              {/* Suggested Fix */}
              {verdict?.suggested_fix && verdict.suggested_fix !== "N/A" && (
                <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                  <h4 className="text-xs uppercase tracking-wide text-green-400 mb-1">
                    Suggested Fairer Version
                  </h4>
                  <p className="text-sm text-gray-300 italic">{verdict.suggested_fix}</p>
                </div>
              )}

              {/* Benchmark Comparison */}
              {result.benchmark_comparison && (
                <div className="bg-cyan-500/10 border border-cyan-500/30 rounded-lg p-4">
                  <h4 className="text-xs uppercase tracking-wide text-cyan-400 mb-2">
                    Industry Benchmark Comparison
                  </h4>
                  <p className="text-xs text-gray-400 mb-2">What a FAIR version of this clause looks like:</p>
                  <p className="text-sm text-gray-300 italic mb-3">&quot;{result.benchmark_comparison.fair_example}&quot;</p>
                  {result.benchmark_comparison.red_flags?.length > 0 && (
                    <div>
                      <p className="text-xs text-red-400 mb-1">Red Flags Detected:</p>
                      <ul className="list-disc list-inside text-xs text-gray-400 space-y-1">
                        {result.benchmark_comparison.red_flags.map((flag: string, i: number) => (
                          <li key={i}>{flag}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Scenario Simulation */}
              {result.scenarios && result.scenarios.length > 0 && (
                <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
                  <h4 className="text-xs uppercase tracking-wide text-amber-400 mb-3">
                    What Could Happen To You (Scenario Simulation)
                  </h4>
                  <div className="space-y-3">
                    {(Array.isArray(result.scenarios) ? result.scenarios : []).map((scenario: Scenario, i: number) => (
                      <div key={i} className="bg-black/20 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-white">{scenario.scenario_title}</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded ${
                            scenario.likelihood === "HIGH" ? "bg-red-500/30 text-red-400" :
                            scenario.likelihood === "MEDIUM" ? "bg-yellow-500/30 text-yellow-400" :
                            "bg-green-500/30 text-green-400"
                          }`}>{scenario.likelihood}</span>
                        </div>
                        <p className="text-xs text-gray-400">{scenario.description}</p>
                        {scenario.financial_impact && (
                          <p className="text-xs text-red-400 mt-1">Financial impact: {scenario.financial_impact}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Negotiation Advice */}
              {result.negotiation_advice && Object.keys(result.negotiation_advice).length > 0 && (
                <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg p-4">
                  <h4 className="text-xs uppercase tracking-wide text-indigo-400 mb-2">
                    Negotiation Strategy
                  </h4>
                  {result.negotiation_advice.negotiation_strategy && (
                    <p className="text-sm text-gray-300 mb-3">{result.negotiation_advice.negotiation_strategy}</p>
                  )}
                  {result.negotiation_advice.talking_points && result.negotiation_advice.talking_points.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-indigo-300 mb-1">Talking Points:</p>
                      <ul className="list-disc list-inside text-xs text-gray-400 space-y-1">
                        {result.negotiation_advice.talking_points.map((point: string, i: number) => (
                          <li key={i}>{point}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {result.negotiation_advice.walk_away_threshold && (
                    <p className="text-xs text-red-400">Walk away if: {result.negotiation_advice.walk_away_threshold}</p>
                  )}
                </div>
              )}

              {/* Matched Exploitative Patterns */}
              {result.matched_patterns && result.matched_patterns.length > 0 && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                  <h4 className="text-xs uppercase tracking-wide text-red-400 mb-2">
                    Known Exploitative Patterns Detected
                  </h4>
                  {result.matched_patterns.map((pattern, i: number) => (
                    <div key={i} className="flex items-start gap-2 mb-2">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                        pattern.risk === "CRITICAL" ? "bg-red-600 text-white" : "bg-yellow-600 text-white"
                      }`}>{pattern.risk}</span>
                      <p className="text-xs text-gray-300">{pattern.explanation}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ============================================================
// MAIN PAGE
// ============================================================
export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [rawText, setRawText] = useState("");
  const [docType, setDocType] = useState("General Contract");
  const [inputMode, setInputMode] = useState<"file" | "url" | "text">("file");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      setFile(acceptedFiles[0]);
      setError("");
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "image/*": [".png", ".jpg", ".jpeg"],
      "text/plain": [".txt"],
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024,
  });

  const handleAnalyze = async () => {
    setLoading(true);
    setError("");
    setResult(null);
    setProgress("Uploading document...");

    try {
      const formData = new FormData();
      formData.append("doc_type", docType);

      if (inputMode === "file" && file) {
        formData.append("file", file);
      } else if (inputMode === "url" && url) {
        formData.append("url", url);
      } else if (inputMode === "text" && rawText) {
        formData.append("raw_text", rawText);
      } else {
        setError("Please provide a document to analyze.");
        setLoading(false);
        return;
      }

      setProgress("Parsing document with Google Document AI...");

      const response = await axios.post(`${API_URL}/api/analyze`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 300000,
      });

      setResult(response.data);
      setProgress("");
    } catch (err: unknown) {
      const errorMsg =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? err.response.data.detail
          : "Analysis failed. Please try again.";
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const docTypes = [
    "General Contract",
    "Terms of Service",
    "Employment Contract",
    "Rental Agreement",
    "NDA / Confidentiality",
    "Freelancer Agreement",
    "Insurance Policy",
    "Loan Agreement",
    "SaaS Agreement",
    "Privacy Policy",
    "Offer Letter",
    "Partnership Agreement",
  ];

  // ============================================================
  // RENDER: Upload Screen
  // ============================================================
  if (!result) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex flex-col">
        {/* Header */}
        <header className="border-b border-white/10 px-6 py-4">
          <div className="max-w-6xl mx-auto flex items-center gap-3">
            <Shield className="w-8 h-8 text-purple-500" />
            <div>
              <h1 className="text-xl font-bold gradient-text">LEXGUARD</h1>
              <p className="text-xs text-gray-500">
                AI Rights & Contract Intelligence System
              </p>
            </div>
            <div className="ml-auto flex items-center gap-2 text-xs text-gray-500">
              <Sparkles className="w-4 h-4" />
              Powered by Google Gemini & GCP
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 flex items-center justify-center px-6 py-12">
          <div className="max-w-2xl w-full">
            {/* Hero */}
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center mb-10"
            >
              <h1 className="text-4xl font-bold mb-3 gradient-text">
                Protect Your Rights
              </h1>
              <p className="text-gray-400 text-lg">
                Upload any contract, agreement, or policy — our adversarial AI agents will
                find every hidden risk before you sign.
              </p>
            </motion.div>

            {/* Google Services Badges */}
            <div className="flex flex-wrap justify-center gap-2 mb-8">
              {[
                { icon: Brain, label: "Gemini 2.5 Pro" },
                { icon: FileText, label: "Document AI" },
                { icon: Eye, label: "Cloud Vision" },
                { icon: Languages, label: "Translation" },
                { icon: Scale, label: "Multi-Agent" },
              ].map((svc, i) => (
                <span
                  key={i}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs text-gray-400"
                >
                  <svc.icon className="w-3.5 h-3.5 text-purple-400" />
                  {svc.label}
                </span>
              ))}
            </div>

            {/* Input Mode Tabs */}
            <div className="flex gap-1 mb-6 bg-white/5 rounded-lg p-1">
              {[
                { mode: "file" as const, icon: Upload, label: "Upload File" },
                { mode: "url" as const, icon: Globe, label: "URL" },
                { mode: "text" as const, icon: FileText, label: "Paste Text" },
              ].map((tab) => (
                <button
                  key={tab.mode}
                  onClick={() => setInputMode(tab.mode)}
                  className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-md text-sm font-medium transition-all ${
                    inputMode === tab.mode
                      ? "bg-purple-600 text-white"
                      : "text-gray-400 hover:text-white"
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* File Upload */}
            {inputMode === "file" && (
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                  isDragActive
                    ? "border-purple-500 bg-purple-500/10"
                    : file
                    ? "border-green-500/50 bg-green-500/5"
                    : "border-white/20 hover:border-purple-500/50"
                }`}
              >
                <input {...getInputProps()} />
                {file ? (
                  <div>
                    <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                    <p className="text-white font-medium">{file.name}</p>
                    <p className="text-gray-500 text-sm mt-1">
                      {(file.size / 1024).toFixed(1)} KB — Click or drop to replace
                    </p>
                  </div>
                ) : (
                  <div>
                    <Upload className="w-12 h-12 text-gray-500 mx-auto mb-3" />
                    <p className="text-gray-300">
                      Drop your contract here, or{" "}
                      <span className="text-purple-400">click to browse</span>
                    </p>
                    <p className="text-gray-500 text-sm mt-2">
                      PDF, DOCX, Images, TXT — up to 10MB
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* URL Input */}
            {inputMode === "url" && (
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/terms-of-service"
                className="w-full px-4 py-4 rounded-xl bg-white/5 border border-white/20 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none text-sm"
              />
            )}

            {/* Text Input */}
            {inputMode === "text" && (
              <textarea
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder="Paste your contract or agreement text here..."
                rows={8}
                className="w-full px-4 py-4 rounded-xl bg-white/5 border border-white/20 text-white placeholder-gray-500 focus:border-purple-500 focus:outline-none text-sm resize-none"
              />
            )}

            {/* Document Type Selector */}
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="w-full mt-4 px-4 py-3 rounded-xl bg-white/5 border border-white/20 text-white text-sm focus:border-purple-500 focus:outline-none appearance-none cursor-pointer"
            >
              {docTypes.map((type) => (
                <option key={type} value={type} className="bg-gray-900">
                  {type}
                </option>
              ))}
            </select>

            {/* Error */}
            {error && (
              <div className="mt-4 p-3 rounded-lg bg-red-500/20 border border-red-500/50 text-red-400 text-sm flex items-center gap-2">
                <XCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {/* Analyze Button */}
            <button
              onClick={handleAnalyze}
              disabled={loading}
              aria-busy={loading}
              aria-label={loading ? "Analyzing contract, please wait" : "Analyze contract for risks"}
              className="w-full mt-6 py-4 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-semibold text-lg hover:from-purple-700 hover:to-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3 focus:outline-none focus:ring-2 focus:ring-purple-400 focus:ring-offset-2 focus:ring-offset-black"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {progress || "Analyzing..."}
                </>
              ) : (
                <>
                  <Shield className="w-5 h-5" />
                  Analyze Contract
                </>
              )}
            </button>

            {/* Loading Progress */}
            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mt-6 space-y-3"
              >
                {[
                  "Parsing document with Google Document AI...",
                  "Detecting language with Cloud Translation...",
                  "RAG: Retrieving legal benchmarks (Vertex AI Embeddings)...",
                  "Agent 1: Corporate Lawyer analyzing...",
                  "Agent 2: Consumer Advocate attacking...",
                  "Agent 3: Judge deliberating...",
                  "Agent 4: Simplifying to plain English...",
                  "Agent 5: Simulating real-world scenarios...",
                  "Agent 6: Generating negotiation strategies...",
                  "Detecting contradictions & ambiguities...",
                  "Computing risk scores...",
                ].map((step, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 2.5 }}
                    className="flex items-center gap-2 text-sm text-gray-400"
                  >
                    <Loader2 className="w-3 h-3 animate-spin text-purple-400" />
                    {step}
                  </motion.div>
                ))}
              </motion.div>
            )}
          </div>
        </main>
      </div>
    );
  }

  // ============================================================
  // RENDER: Results Dashboard
  // ============================================================
  const sortedClauses = [...result.clause_results].sort((a, b) => {
    const scoreA = typeof a.verdict?.risk_score === "number" ? a.verdict.risk_score : 0;
    const scoreB = typeof b.verdict?.risk_score === "number" ? b.verdict.risk_score : 0;
    return scoreB - scoreA;
  });

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Header */}
      <header className="border-b border-white/10 px-6 py-4 sticky top-0 bg-[#0a0a0a]/90 backdrop-blur-lg z-50">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-purple-500" />
            <h1 className="text-xl font-bold gradient-text">LEXGUARD</h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={async () => {
                try {
                  const res = await axios.post(`${API_URL}/api/report/pdf`, result, {
                    responseType: 'blob',
                  });
                  const url = window.URL.createObjectURL(new Blob([res.data]));
                  const link = document.createElement('a');
                  link.href = url;
                  link.setAttribute('download', 'LexGuard_Risk_Report.pdf');
                  document.body.appendChild(link);
                  link.click();
                  link.remove();
                } catch { alert('PDF generation failed'); }
              }}
              className="px-4 py-2 rounded-lg bg-purple-600 text-sm text-white hover:bg-purple-700 transition flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Download Report
            </button>
            <button
              onClick={() => {
                setResult(null);
                setFile(null);
                setUrl("");
                setRawText("");
              }}
              className="px-4 py-2 rounded-lg bg-white/10 text-sm text-gray-300 hover:bg-white/20 transition"
            >
              Analyze Another
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Top Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          {/* Risk Score */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`glass-card rounded-2xl p-6 text-center ${
              result.overall_risk_score >= 8
                ? "pulse-red"
                : result.overall_risk_score >= 5
                ? "pulse-yellow"
                : ""
            }`}
          >
            <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">
              Overall Risk
            </p>
            <p className={`text-5xl font-bold ${getRiskColor(result.overall_risk_score)}`}>
              {result.overall_risk_score}
            </p>
            <p className="text-gray-500 text-sm">/10</p>
          </motion.div>

          {/* Grade */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.1 }}
            className="glass-card rounded-2xl p-6 text-center"
          >
            <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">
              Grade
            </p>
            <p className={`text-5xl font-bold ${getGradeColor(result.risk_grade)}`}>
              {result.risk_grade}
            </p>
            <p className="text-gray-500 text-sm mt-1">{result.recommendation}</p>
          </motion.div>

          {/* Issue Breakdown */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
            className="glass-card rounded-2xl p-6"
          >
            <p className="text-xs uppercase tracking-wide text-gray-500 mb-3">
              Issue Breakdown
            </p>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-red-500 text-sm flex items-center gap-1.5">
                  <XCircle className="w-3.5 h-3.5" /> Critical
                </span>
                <span className="text-white font-bold">{result.critical_issues}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-yellow-500 text-sm flex items-center gap-1.5">
                  <AlertTriangle className="w-3.5 h-3.5" /> Warnings
                </span>
                <span className="text-white font-bold">{result.warnings_count}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-green-500 text-sm flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5" /> Safe
                </span>
                <span className="text-white font-bold">{result.safe_count}</span>
              </div>
            </div>
          </motion.div>

          {/* Metadata */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
            className="glass-card rounded-2xl p-6"
          >
            <p className="text-xs uppercase tracking-wide text-gray-500 mb-3">
              Analysis Info
            </p>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Clauses</span>
                <span className="text-white">{result.total_clauses}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Language</span>
                <span className="text-white">
                  {result.language_info?.original_language?.toUpperCase() || "EN"}
                  {result.language_info?.was_translated && " -> EN"}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Parser</span>
                <span className="text-white text-xs">{result.parsing_method}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Sentiment</span>
                <span className="text-white text-xs">
                  {result.nlp_sentiment?.interpretation || "N/A"}
                </span>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Risk Bar Visual */}
        <div className="glass-card rounded-2xl p-6 mb-8">
          <p className="text-xs uppercase tracking-wide text-gray-500 mb-3">
            Clause Risk Distribution
          </p>
          <div className="flex gap-1 h-8 rounded-lg overflow-hidden">
            {sortedClauses.map((c, i) => {
              const score =
                typeof c.verdict?.risk_score === "number" ? c.verdict.risk_score : 5;
              return (
                <div
                  key={i}
                  className={`flex-1 ${
                    score >= 8
                      ? "bg-red-500"
                      : score >= 5
                      ? "bg-yellow-500"
                      : "bg-green-500"
                  } hover:opacity-80 transition-opacity cursor-pointer relative group`}
                  title={`${c.clause.title}: ${score}/10`}
                >
                  <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition pointer-events-none">
                    {c.clause.title}: {score}/10
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex justify-between mt-2 text-xs text-gray-500">
            <span>Highest Risk</span>
            <span>Lowest Risk</span>
          </div>
        </div>

        {/* Executive Summary */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card rounded-2xl p-6 mb-8"
        >
          <h2 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400" />
            Executive Summary
          </h2>
          <p className="text-gray-300 leading-relaxed whitespace-pre-line">
            {result.executive_summary}
          </p>
        </motion.div>

        {/* Contradictions & Document-Level Issues */}
        {result.contradictions && (
          <div className="glass-card rounded-2xl p-6 mb-8">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
              Document-Level Issues
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Contradictions */}
              {result.contradictions.contradictions && result.contradictions.contradictions.length > 0 && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                  <h4 className="text-xs uppercase tracking-wide text-red-400 mb-2">Internal Contradictions</h4>
                  {result.contradictions.contradictions.map((c, i) => (
                    <div key={i} className="mb-2 text-xs text-gray-300">
                      <p className="text-red-300 font-medium">{c.explanation}</p>
                    </div>
                  ))}
                </div>
              )}
              {/* Missing Protections */}
              {result.contradictions.missing_protections && result.contradictions.missing_protections.length > 0 && (
                <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                  <h4 className="text-xs uppercase tracking-wide text-yellow-400 mb-2">Missing Standard Protections</h4>
                  <ul className="list-disc list-inside text-xs text-gray-300 space-y-1">
                    {result.contradictions.missing_protections.map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
              )}
              {/* Ambiguities */}
              {result.contradictions.ambiguities && result.contradictions.ambiguities.length > 0 && (
                <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
                  <h4 className="text-xs uppercase tracking-wide text-orange-400 mb-2">Ambiguous Language</h4>
                  {result.contradictions.ambiguities.map((a, i) => (
                    <div key={i} className="mb-2 text-xs">
                      <span className="text-orange-300 font-medium">&quot;{a.ambiguous_term}&quot;</span>
                      <span className="text-gray-400"> — could mean: {a.possible_interpretations?.join(" OR ")}</span>
                    </div>
                  ))}
                </div>
              )}
              {/* Unusual Terms */}
              {result.contradictions.unusual_terms && result.contradictions.unusual_terms.length > 0 && (
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4">
                  <h4 className="text-xs uppercase tracking-wide text-purple-400 mb-2">Unusual Terms</h4>
                  {result.contradictions.unusual_terms.map((u, i) => (
                    <p key={i} className="text-xs text-gray-300 mb-1">{u.why_unusual}</p>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Clause-by-Clause Analysis */}
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Scale className="w-5 h-5 text-purple-400" />
          Clause-by-Clause Analysis
          <span className="text-sm text-gray-500 font-normal">
            (sorted by risk, click to expand)
          </span>
        </h2>

        {sortedClauses.map((clauseResult, index) => (
          <ClauseCard key={index} result={clauseResult} index={index} />
        ))}

        {/* Footer */}
        <footer className="text-center py-12 text-gray-600 text-sm" role="contentinfo">
          <p>
            LexGuard — Built with Google Gemini, Document AI, Cloud Vision, Cloud
            Translation, Cloud NL API, Firestore, Cloud Run & Firebase
          </p>
          <p className="mt-1">Adversarial Multi-Agent Contract Intelligence</p>
        </footer>
      </main>
    </div>
  );
}
