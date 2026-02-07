"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useRouter, useParams } from "next/navigation";

interface Post {
  id: string;
  topic: string;
  tone: string;
  contentType: string;
  content: string;
  status: "draft" | "edited" | "used";
  editHistory: { timestamp: string; previousContent: string; newContent: string }[];
  createdAt: string;
  updatedAt: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export default function PostDetailPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();
  const postId = params.id as string;

  const [post, setPost] = useState<Post | null>(null);
  const [editedContent, setEditedContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");
  
  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [refining, setRefining] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  useEffect(() => {
    if (session?.user && postId) {
      loadPost();
    }
  }, [session, postId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const loadPost = async () => {
    try {
      const res = await fetch(`/api/posts/${postId}`);
      if (res.ok) {
        const data = await res.json();
        setPost(data);
        setEditedContent(data.content);
      } else if (res.status === 404) {
        router.push("/posts");
      }
    } catch (err) {
      console.error("Failed to load post:", err);
      setError("Failed to load post");
    } finally {
      setLoading(false);
    }
  };

  const savePost = async () => {
    if (!post || editedContent === post.content) return;
    
    setSaving(true);
    setError("");
    
    try {
      const res = await fetch(`/api/posts/${postId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editedContent }),
      });
      
      if (res.ok) {
        const data = await res.json();
        setPost(data);
        setSaved(true);
        setTimeout(() => setSaved(false), 2000);
      } else {
        throw new Error("Failed to save");
      }
    } catch (err) {
      setError("Failed to save post. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  const copyPost = () => {
    // Try modern clipboard API first, fallback for non-HTTPS
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(editedContent);
    } else {
      // Fallback for HTTP contexts
      const textarea = document.createElement('textarea');
      textarea.value = editedContent;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const sendChatMessage = async () => {
    if (!chatInput.trim() || refining) return;
    
    const userMessage = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setRefining(true);
    
    try {
      const res = await fetch(`/api/posts/${postId}/refine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
      });
      
      if (res.ok) {
        const data = await res.json();
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Here's the revised version:" },
        ]);
        setEditedContent(data.refinedContent);
      } else {
        const data = await res.json();
        throw new Error(data.error || "Failed to refine");
      }
    } catch (err: any) {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Sorry, I couldn't refine the post: ${err.message}` },
      ]);
    } finally {
      setRefining(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  };

  if (status === "loading" || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  if (!session || !post) {
    return null;
  }

  const hasChanges = editedContent !== post.content;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Link
              href="/posts"
              className="text-slate-400 hover:text-white text-sm mb-2 inline-flex items-center gap-1 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              Back to Posts
            </Link>
            <h1 className="text-2xl font-bold text-white">{post.topic}</h1>
            <p className="text-slate-400 text-sm mt-1 capitalize">{post.tone} • {post.contentType}</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={copyPost}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                copied
                  ? "bg-green-600 text-white"
                  : "bg-slate-700 hover:bg-slate-600 text-white"
              }`}
            >
              {copied ? "✓ Copied" : "Copy"}
            </button>
            <button
              onClick={savePost}
              disabled={saving || !hasChanges}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                saved
                  ? "bg-green-600 text-white"
                  : hasChanges
                  ? "bg-blue-600 hover:bg-blue-700 text-white"
                  : "bg-slate-700 text-slate-500 cursor-not-allowed"
              }`}
            >
              {saving ? "Saving..." : saved ? "✓ Saved" : "Save Changes"}
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/50 text-red-400 px-4 py-3 rounded-xl text-sm mb-6">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Post Editor */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-700 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">Post Content</h2>
              {hasChanges && (
                <span className="text-xs text-amber-400 bg-amber-400/10 px-2 py-1 rounded">
                  Unsaved changes
                </span>
              )}
            </div>
            <textarea
              value={editedContent}
              onChange={(e) => setEditedContent(e.target.value)}
              className="w-full h-[500px] p-6 bg-transparent text-slate-200 font-sans leading-relaxed resize-none focus:outline-none"
              placeholder="Post content..."
            />
          </div>

          {/* Chat Interface */}
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-700">
              <h2 className="text-lg font-semibold text-white">Refine with AI</h2>
              <p className="text-slate-400 text-sm">Describe how you'd like to change the post</p>
            </div>
            
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-[300px] max-h-[400px]">
              {chatMessages.length === 0 ? (
                <div className="text-center text-slate-500 py-8">
                  <svg
                    className="w-12 h-12 mx-auto mb-3 opacity-50"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                    />
                  </svg>
                  <p className="text-sm">Try these suggestions:</p>
                  <div className="mt-3 space-y-2">
                    {[
                      "Make it more casual",
                      "Add a stronger hook",
                      "Make it shorter",
                      "Add a call to action",
                    ].map((suggestion) => (
                      <button
                        key={suggestion}
                        onClick={() => {
                          setChatInput(suggestion);
                        }}
                        className="block w-full text-left px-3 py-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg text-sm text-slate-300 transition-colors"
                      >
                        "{suggestion}"
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                chatMessages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm ${
                        msg.role === "user"
                          ? "bg-blue-600 text-white"
                          : "bg-slate-700 text-slate-200"
                      }`}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))
              )}
              {refining && (
                <div className="flex justify-start">
                  <div className="bg-slate-700 text-slate-200 px-4 py-2 rounded-2xl text-sm flex items-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                    Refining...
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
            
            {/* Chat Input */}
            <div className="p-4 border-t border-slate-700">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="e.g., Make it more conversational..."
                  className="flex-1 px-4 py-3 bg-slate-900/50 border border-slate-600 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  disabled={refining}
                />
                <button
                  onClick={sendChatMessage}
                  disabled={refining || !chatInput.trim()}
                  className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-xl transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Edit History */}
        {post.editHistory.length > 0 && (
          <div className="mt-8">
            <h3 className="text-lg font-semibold text-white mb-4">Edit History</h3>
            <div className="space-y-3">
              {post.editHistory.slice().reverse().map((edit, i) => (
                <div
                  key={i}
                  className="bg-slate-800/30 border border-slate-700 rounded-xl p-4"
                >
                  <div className="text-xs text-slate-500 mb-2">
                    {new Date(edit.timestamp).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                  </div>
                  <button
                    onClick={() => setEditedContent(edit.newContent)}
                    className="text-sm text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    Restore this version
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
