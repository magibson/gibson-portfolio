"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import { UserSettings, DEFAULT_SETTINGS, AUDIENCES } from "@/lib/types";

interface WritingExample {
  id: string;
  content: string;
  source: string;
  createdAt: string;
}

interface UsageInfo {
  used: number;
  limit: number;
  remaining: number;
  resetsAt: string;
}

// Debounce hook for auto-save
function useDebouncedSave(callback: () => Promise<void>, delay: number) {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  const debouncedSave = useCallback(() => {
    setSaveStatus('saving');
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(async () => {
      try {
        await callback();
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus('idle'), 2000);
      } catch (error) {
        setSaveStatus('error');
        setTimeout(() => setSaveStatus('idle'), 3000);
      }
    }, delay);
  }, [callback, delay]);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return { debouncedSave, saveStatus };
}

// Typewriter effect component
function TypeWriter({ text, speed = 30 }: { text: string; speed?: number }) {
  const [displayedText, setDisplayedText] = useState("");
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    setDisplayedText("");
    setIsComplete(false);
    let index = 0;
    const timer = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1));
        index++;
      } else {
        setIsComplete(true);
        clearInterval(timer);
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, speed]);

  return (
    <span>
      {displayedText}
      {!isComplete && <span className="animate-pulse">|</span>}
    </span>
  );
}

// Auto-save indicator component
function SaveIndicator({ status }: { status: 'idle' | 'saving' | 'saved' | 'error' }) {
  if (status === 'idle') return null;
  
  return (
    <div className={`fixed bottom-6 right-6 flex items-center gap-2 px-4 py-2 rounded-lg shadow-lg transition-all duration-300 ${
      status === 'saving' ? 'bg-slate-700 text-slate-300' :
      status === 'saved' ? 'bg-green-600/90 text-white' :
      'bg-red-600/90 text-white'
    }`}>
      {status === 'saving' && (
        <>
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Saving...</span>
        </>
      )}
      {status === 'saved' && (
        <>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="text-sm">Saved</span>
        </>
      )}
      {status === 'error' && (
        <>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          <span className="text-sm">Save failed</span>
        </>
      )}
    </div>
  );
}

// Segmented control for discrete values
function SegmentedControl({
  value,
  onChange,
  options,
  label,
}: {
  value: number;
  onChange: (value: number) => void;
  options: number[];
  label: string;
}) {
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const getValueFromPosition = (clientX: number) => {
    if (!containerRef.current) return value;
    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const percentage = Math.max(0, Math.min(1, x / rect.width));
    const index = Math.round(percentage * (options.length - 1));
    return options[index];
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    onChange(getValueFromPosition(e.clientX));
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      onChange(getValueFromPosition(e.clientX));
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleMouseLeave = () => {
    setIsDragging(false);
  };

  const selectedIndex = options.indexOf(value);
  const selectorWidth = 100 / options.length;
  const selectorLeft = selectedIndex * selectorWidth;

  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        <label className="text-sm font-medium text-slate-300">{label}</label>
        <span className="text-2xl font-bold text-white">{value}</span>
      </div>
      <div 
        ref={containerRef}
        className="relative bg-slate-900/50 p-1 rounded-xl select-none cursor-pointer"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      >
        <div 
          className="absolute top-1 bottom-1 bg-blue-600 rounded-lg"
          style={{
            width: `calc(${selectorWidth}% - 4px)`,
            left: `calc(${selectorLeft}% + 2px)`,
            transform: isDragging ? 'scale(1.15)' : 'scale(1)',
            transition: isDragging ? 'left 0.05s ease-out, transform 0.1s' : 'left 0.15s ease-out, transform 0.15s',
          }}
        />
        <div className="relative flex">
          {options.map((opt) => (
            <div
              key={opt}
              className={`flex-1 py-2 text-sm font-medium rounded-lg text-center pointer-events-none z-10 transition-colors ${
                value === opt ? 'text-white' : 'text-slate-400'
              }`}
            >
              {opt}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Usage meter component
function UsageMeter({ usage }: { usage: UsageInfo }) {
  const percentage = (usage.used / usage.limit) * 100;
  const isLow = usage.remaining <= 5;
  const isEmpty = usage.remaining === 0;
  
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm text-slate-400">Weekly Usage</span>
        <span className={`text-sm font-medium ${isEmpty ? 'text-red-400' : isLow ? 'text-yellow-400' : 'text-slate-300'}`}>
          {usage.remaining} posts remaining
        </span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div 
          className={`h-full transition-all duration-500 ${
            isEmpty ? 'bg-red-500' : isLow ? 'bg-yellow-500' : 'bg-blue-500'
          }`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="flex justify-between items-center mt-2">
        <span className="text-xs text-slate-500">{usage.used} of {usage.limit} used</span>
        <span className="text-xs text-slate-500">Resets {usage.resetsAt}</span>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [writingExamples, setWritingExamples] = useState<WritingExample[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newWebsite, setNewWebsite] = useState("");
  const [newExample, setNewExample] = useState("");
  const [addingExample, setAddingExample] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generationSuccess, setGenerationSuccess] = useState<{ postCount: number } | null>(null);
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  
  // Greeting state
  const [greeting, setGreeting] = useState<string>("");
  const [greetingLoading, setGreetingLoading] = useState(true);

  // Track if initial load is done
  const initialLoadDone = useRef(false);

  const saveSettingsToServer = useCallback(async () => {
    const res = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        postsPerBatch: settings.postsPerBatch,
        postLength: settings.postLength,
        emailAddress: settings.emailAddress,
        sourceWebsites: settings.sourceWebsites,
        audience: settings.audience,
        customTopics: settings.customTopics,
        aiInstructions: settings.aiInstructions,
      }),
    });

    if (!res.ok) {
      throw new Error("Failed to save");
    }
  }, [settings]);

  const { debouncedSave, saveStatus } = useDebouncedSave(saveSettingsToServer, 400);

  useEffect(() => {
    if (initialLoadDone.current) {
      debouncedSave();
    }
  }, [settings, debouncedSave]);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  useEffect(() => {
    if (session?.user) {
      loadSettings();
      loadWritingExamples();
      loadGreeting();
      loadUsage();
    }
  }, [session]);

  const loadGreeting = async () => {
    setGreetingLoading(true);
    try {
      const res = await fetch("/api/greeting");
      if (res.ok) {
        const data = await res.json();
        setGreeting(data.greeting);
      }
    } catch (err) {
      console.error("Failed to load greeting:", err);
      setGreeting(`Welcome back!`);
    } finally {
      setGreetingLoading(false);
    }
  };

  const loadUsage = async () => {
    try {
      const res = await fetch("/api/usage");
      if (res.ok) {
        const data = await res.json();
        setUsage(data);
      }
    } catch (err) {
      console.error("Failed to load usage:", err);
    }
  };

  const loadSettings = async () => {
    try {
      const res = await fetch("/api/settings");
      if (res.ok) {
        const data = await res.json();
        setSettings({
          postsPerBatch: data.postsPerBatch,
          batchCount: 1,
          postLength: data.postLength,
          emailAddress: data.emailAddress,
          sourceWebsites: data.sourceWebsites,
          audience: data.audience || "young-professionals",
          customTopics: data.customTopics || [],
          schedules: [],
          writingStyle: data.writingStyle || "",
          aiInstructions: data.aiInstructions || "",
        });
      }
    } catch (err) {
      console.error("Failed to load settings:", err);
    } finally {
      setLoading(false);
      setTimeout(() => {
        initialLoadDone.current = true;
      }, 100);
    }
  };

  const loadWritingExamples = async () => {
    try {
      const res = await fetch("/api/writing-examples");
      if (res.ok) {
        const data = await res.json();
        setWritingExamples(data.examples);
      }
    } catch (err) {
      console.error("Failed to load writing examples:", err);
    }
  };

  const addWebsite = () => {
    if (!newWebsite.trim()) return;
    let url = newWebsite.trim();
    if (!url.startsWith("http")) url = "https://" + url;
    setSettings({
      ...settings,
      sourceWebsites: [...settings.sourceWebsites, url],
    });
    setNewWebsite("");
  };

  const removeWebsite = (url: string) => {
    setSettings({
      ...settings,
      sourceWebsites: settings.sourceWebsites.filter((w) => w !== url),
    });
  };

  const addWritingExample = async () => {
    if (!newExample.trim()) return;
    setAddingExample(true);
    
    try {
      const res = await fetch("/api/writing-examples", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: newExample, source: "manual" }),
      });
      
      if (res.ok) {
        const data = await res.json();
        setWritingExamples([data.example, ...writingExamples]);
        setNewExample("");
      }
    } catch (err) {
      console.error("Failed to add example:", err);
    } finally {
      setAddingExample(false);
    }
  };

  const removeWritingExample = async (id: string) => {
    try {
      const res = await fetch(`/api/writing-examples?id=${id}`, {
        method: "DELETE",
      });
      
      if (res.ok) {
        setWritingExamples(writingExamples.filter((e) => e.id !== id));
      }
    } catch (err) {
      console.error("Failed to delete example:", err);
    }
  };

  const handleGenerateNow = async () => {
    if (usage && usage.remaining < settings.postsPerBatch) {
      setError(`You can only generate ${usage.remaining} more posts this week. Reduce the count or wait for your limit to reset.`);
      return;
    }
    
    setGenerating(true);
    setError("");
    setGenerationSuccess(null);
    
    try {
      const res = await fetch("/api/batch/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          count: settings.postsPerBatch,
          sendEmail: false,
          baseUrl: window.location.origin,
        }),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.error || "Failed to generate");
      }
      
      setGenerationSuccess({
        postCount: data.posts?.length || 0,
      });
      
      // Refresh usage after generation
      loadUsage();
      
      setTimeout(() => {
        router.push("/posts");
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to generate posts. Please try again.");
    } finally {
      setGenerating(false);
    }
  };

  if (status === "loading" || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  const canGenerate = usage ? usage.remaining >= settings.postsPerBatch : true;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white mb-3">LinkedIn Content Generator</h1>
            {!greetingLoading && greeting && (
              <p className="text-lg text-blue-400 font-medium">
                <TypeWriter text={greeting} speed={25} />
              </p>
            )}
          </div>
          <div className="flex items-center gap-4 flex-shrink-0">
            <Link
              href="/posts"
              className="flex items-center gap-2 px-5 py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors whitespace-nowrap"
            >
              <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              My Posts
            </Link>
            <button
              onClick={() => signOut()}
              className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors whitespace-nowrap"
            >
              Sign Out
            </button>
          </div>
        </div>

        {/* Usage Meter */}
        {usage && (
          <div className="mb-6">
            <UsageMeter usage={usage} />
          </div>
        )}

        {/* Generate Card */}
        <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-2xl p-6 shadow-lg mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Generate Posts</h2>
              <p className="text-blue-100/80 text-sm">
                Create {settings.postsPerBatch} {settings.postsPerBatch === 1 ? 'post' : 'posts'} instantly
              </p>
            </div>
          </div>
          
          <button
            onClick={handleGenerateNow}
            disabled={generating || !canGenerate}
            className="w-full py-3 bg-white/20 hover:bg-white/30 disabled:bg-white/10 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {generating ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Generating...
              </>
            ) : !canGenerate ? (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m0 0v2m0-2h2m-2 0H10m4-6a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
                Weekly Limit Reached
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Generate Posts
              </>
            )}
          </button>
          
          {!canGenerate && usage && (
            <p className="text-blue-200/70 text-sm text-center mt-3">
              You have {usage.remaining} posts remaining. Reduce count or wait until {usage.resetsAt}.
            </p>
          )}
        </div>

        {/* Success Message */}
        {generationSuccess && (
          <div className="bg-green-500/10 border border-green-500/50 text-green-400 px-4 py-3 rounded-xl text-sm mb-6 flex items-center gap-3">
            <svg className="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span>
              Generated {generationSuccess.postCount} posts! Redirecting...
            </span>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-xl text-sm mb-6">
            {error}
          </div>
        )}

        <h2 className="text-xl font-bold text-white mb-6">Settings</h2>

        <div className="space-y-8">
          {/* Generation Settings */}
          <section className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Generation Settings</h2>
            
            <SegmentedControl
              value={settings.postsPerBatch}
              onChange={(value) => setSettings({ ...settings, postsPerBatch: value })}
              options={[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
              label="Posts to generate"
            />
          </section>

          {/* Source Websites */}
          <section className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Source Websites</h2>
            <p className="text-slate-400 text-sm mb-4">Websites to pull topics and inspiration from</p>

            {settings.sourceWebsites.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-4">
                {settings.sourceWebsites.map((url) => (
                  <div
                    key={url}
                    className="flex items-center gap-2 bg-slate-900/30 px-3 py-2 rounded-lg"
                  >
                    <span className="text-slate-300 text-sm">{new URL(url).hostname}</span>
                    <button
                      onClick={() => removeWebsite(url)}
                      className="text-slate-500 hover:text-red-400 transition-colors"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="mb-4">
              <p className="text-slate-500 text-xs mb-2">Popular financial news sources:</p>
              <div className="flex flex-wrap gap-2">
                {[
                  { name: "Kiplinger", url: "https://www.kiplinger.com" },
                  { name: "Yahoo Finance", url: "https://finance.yahoo.com" },
                  { name: "CNBC", url: "https://www.cnbc.com" },
                  { name: "Barchart", url: "https://www.barchart.com" },
                  { name: "MarketWatch", url: "https://www.marketwatch.com" },
                  { name: "Bloomberg", url: "https://www.bloomberg.com" },
                  { name: "Investopedia", url: "https://www.investopedia.com" },
                  { name: "The Motley Fool", url: "https://www.fool.com" },
                ].filter(s => !settings.sourceWebsites.includes(s.url)).map((source) => (
                  <button
                    key={source.url}
                    onClick={() => setSettings({ 
                      ...settings, 
                      sourceWebsites: [...settings.sourceWebsites, source.url] 
                    })}
                    className="px-3 py-1.5 bg-slate-700/50 hover:bg-blue-600/30 border border-slate-600 hover:border-blue-500 text-slate-300 hover:text-white text-sm rounded-lg transition-all"
                  >
                    + {source.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex gap-3">
              <input
                type="text"
                value={newWebsite}
                onChange={(e) => setNewWebsite(e.target.value)}
                placeholder="e.g., investmentnews.com"
                className="flex-1 px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={addWebsite}
                className="px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition-colors"
              >
                Add
              </button>
            </div>
          </section>

          {/* Target Audience */}
          <section className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Target Audience</h2>
            <p className="text-slate-400 text-sm mb-4">Content topics will be curated based on your selected audience</p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
              {AUDIENCES.map((audience) => (
                <button
                  key={audience.id}
                  onClick={() => setSettings({ ...settings, audience: audience.id })}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    settings.audience === audience.id
                      ? "bg-blue-600/20 border-blue-500"
                      : "bg-slate-900/30 border-slate-600 hover:border-slate-500"
                  }`}
                >
                  <div className={`font-medium ${settings.audience === audience.id ? "text-white" : "text-slate-300"}`}>
                    {audience.label}
                  </div>
                  <div className={`text-sm mt-1 ${settings.audience === audience.id ? "text-blue-200" : "text-slate-500"}`}>
                    {audience.description}
                  </div>
                </button>
              ))}
            </div>

            {settings.audience && settings.audience !== "custom" && (
              <div className="bg-slate-900/30 rounded-xl p-4">
                <p className="text-slate-400 text-xs mb-2">
                  <svg className="w-4 h-4 inline mr-1 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Content will focus on these topics:
                </p>
                <div className="flex flex-wrap gap-2">
                  {AUDIENCES.find(a => a.id === settings.audience)?.topics.map((topic) => (
                    <span
                      key={topic}
                      className="px-3 py-1.5 bg-slate-800 text-slate-300 text-sm rounded-full capitalize"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </section>

          {/* Post Preferences */}
          <section className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Post Preferences</h2>

            <div>
              <div className="flex justify-between items-center mb-3">
                <label className="text-sm font-medium text-slate-300">
                  Preferred post length
                </label>
                <span className="text-lg font-bold text-white capitalize">
                  {settings.postLength} 
                  <span className="text-sm font-normal text-slate-400 ml-1">
                    (~{settings.postLength === "short" ? "100" : settings.postLength === "medium" ? "200" : "300"} words)
                  </span>
                </span>
              </div>
              <div className="flex gap-2 bg-slate-900/50 p-1 rounded-xl">
                {(['short', 'medium', 'long'] as const).map((length) => (
                  <button
                    key={length}
                    onClick={() => setSettings({ ...settings, postLength: length })}
                    className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all capitalize ${
                      settings.postLength === length
                        ? 'bg-blue-600 text-white shadow-lg'
                        : 'text-slate-400 hover:text-white hover:bg-slate-700/50'
                    }`}
                  >
                    {length}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* AI Instructions */}
          <section className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
            <h2 className="text-xl font-semibold text-white mb-4">AI Instructions</h2>
            <p className="text-slate-400 text-sm mb-4">
              Custom rules for the AI to follow when generating posts
            </p>

            <textarea
              value={settings.aiInstructions}
              onChange={(e) => setSettings({ ...settings, aiInstructions: e.target.value })}
              placeholder="Examples:&#10;• Never use emojis&#10;• Always end with a question&#10;• Keep a professional tone&#10;• Don't use buzzwords like 'synergy'"
              className="w-full h-32 px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            />
            <p className="text-slate-500 text-xs mt-2">
              These instructions will be applied to every post generated
            </p>
          </section>

          {/* Writing Examples */}
          <section className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Writing Examples</h2>
            <p className="text-slate-400 text-sm mb-4">
              Add examples of your writing style. The AI will learn from these to match your voice.
            </p>

            {writingExamples.length > 0 && (
              <div className="space-y-3 mb-4">
                {writingExamples.map((example) => (
                  <div
                    key={example.id}
                    className="bg-slate-900/30 px-4 py-3 rounded-xl"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-slate-300 text-sm whitespace-pre-wrap line-clamp-4">
                        {example.content}
                      </p>
                      <button
                        onClick={() => removeWritingExample(example.id)}
                        className="text-slate-500 hover:text-red-400 transition-colors flex-shrink-0"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                    <div className="text-slate-500 text-xs mt-2">
                      Added {new Date(example.createdAt).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="space-y-3">
              <textarea
                value={newExample}
                onChange={(e) => setNewExample(e.target.value)}
                placeholder="Paste an example LinkedIn post you've written that represents your voice..."
                className="w-full h-32 px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
              <button
                onClick={addWritingExample}
                disabled={addingExample || !newExample.trim()}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 text-white rounded-xl transition-colors"
              >
                {addingExample ? "Adding..." : "Add Example"}
              </button>
            </div>
          </section>

          {/* Email Delivery */}
          <section className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
            <h2 className="text-xl font-semibold text-white mb-4">Email Notifications</h2>
            <p className="text-slate-400 text-sm mb-4">Receive your generated posts via email</p>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Email address
              </label>
              <input
                type="email"
                value={settings.emailAddress}
                onChange={(e) => setSettings({ ...settings, emailAddress: e.target.value })}
                placeholder="your@email.com"
                className="w-full px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </section>
        </div>
      </div>

      <SaveIndicator status={saveStatus} />
    </div>
  );
}
