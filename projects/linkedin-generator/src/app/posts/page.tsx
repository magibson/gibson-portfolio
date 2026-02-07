"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";

interface Post {
  id: string;
  topic: string;
  tone: string;
  contentType: string;
  content: string;
  status: "draft" | "edited" | "used";
  sourceArticleUrl: string | null;
  sourceArticleTitle: string | null;
  sourceArticleImage: string | null;
  audience: string | null;
  createdAt: string;
  updatedAt: string;
  batch: {
    id: string;
    scheduledFor: string;
    generatedAt: string | null;
  } | null;
}

const AUDIENCE_LABELS: Record<string, string> = {
  "young-professionals": "Young Professionals",
  "young-families": "Young Families",
  "pre-retirees": "Pre-Retirees",
  "retirees": "Retirees",
  "custom": "Custom Audience",
};

// Loading skeleton for post cards
function PostSkeleton() {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-2xl overflow-hidden animate-pulse">
      <div className="flex items-center justify-between px-6 py-3 border-b border-slate-700">
        <div className="flex gap-2">
          <div className="h-6 w-24 bg-slate-700 rounded-full"></div>
          <div className="h-6 w-16 bg-slate-700 rounded-full"></div>
        </div>
        <div className="flex gap-2">
          <div className="h-8 w-20 bg-slate-700 rounded-lg"></div>
          <div className="h-8 w-16 bg-slate-700 rounded-lg"></div>
          <div className="h-8 w-14 bg-slate-700 rounded-lg"></div>
        </div>
      </div>
      <div className="px-6 py-4 space-y-3">
        <div className="h-4 bg-slate-700 rounded w-full"></div>
        <div className="h-4 bg-slate-700 rounded w-5/6"></div>
        <div className="h-4 bg-slate-700 rounded w-4/6"></div>
        <div className="h-4 bg-slate-700 rounded w-full"></div>
        <div className="h-4 bg-slate-700 rounded w-3/4"></div>
      </div>
      <div className="px-6 py-3 bg-slate-900/30">
        <div className="h-3 w-32 bg-slate-700 rounded"></div>
      </div>
    </div>
  );
}

export default function PostsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [audience, setAudience] = useState<string>("young-professionals");

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/login");
    }
  }, [status, router]);

  useEffect(() => {
    if (session?.user) {
      loadPosts();
    }
  }, [session]);

  const loadPosts = async () => {
    try {
      const res = await fetch("/api/posts");
      if (res.ok) {
        const data = await res.json();
        setPosts(data.posts);
        if (data.audience) {
          setAudience(data.audience);
        }
      }
    } catch (err) {
      console.error("Failed to load posts:", err);
    } finally {
      setLoading(false);
    }
  };

  const copyPost = (id: string, content: string) => {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(content);
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = content;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const toggleUsed = async (post: Post) => {
    const newStatus = post.status === "used" ? "draft" : "used";
    try {
      const res = await fetch(`/api/posts/${post.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      
      if (res.ok) {
        setPosts(posts.map((p) => 
          p.id === post.id ? { ...p, status: newStatus } : p
        ));
      }
    } catch (err) {
      console.error("Failed to update post status:", err);
    }
  };

  const deletePost = async (postId: string) => {
    if (!confirm("Delete this post?")) return;
    
    try {
      const res = await fetch(`/api/posts/${postId}`, {
        method: "DELETE",
      });
      
      if (res.ok) {
        setPosts(posts.filter((p) => p.id !== postId));
      }
    } catch (err) {
      console.error("Failed to delete post:", err);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "used":
        return (
          <span className="px-2.5 py-1 bg-green-500/20 text-green-400 text-xs font-medium rounded-full">
            ✓ Used
          </span>
        );
      case "edited":
        return (
          <span className="px-2.5 py-1 bg-blue-500/20 text-blue-400 text-xs font-medium rounded-full">
            Edited
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 bg-slate-600/30 text-slate-400 text-xs font-medium rounded-full">
            Draft
          </span>
        );
    }
  };

  const filteredPosts = filterStatus === "all" 
    ? posts 
    : posts.filter((p) => p.status === filterStatus);

  // Calculate stats
  const stats = {
    total: posts.length,
    draft: posts.filter(p => p.status === "draft").length,
    used: posts.filter(p => p.status === "used").length,
  };

  if (status === "loading") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <div className="max-w-4xl mx-auto px-6 py-12">
          <div className="animate-pulse mb-8">
            <div className="h-8 w-32 bg-slate-700 rounded mb-2"></div>
            <div className="h-4 w-24 bg-slate-700 rounded"></div>
          </div>
          <div className="space-y-4">
            <PostSkeleton />
            <PostSkeleton />
            <PostSkeleton />
          </div>
        </div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">My Posts</h1>
            <p className="text-slate-400 mt-1">
              {stats.total} total · {stats.draft} ready to use · {stats.used} used
            </p>
          </div>
          <Link
            href="/settings"
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Dashboard
          </Link>
        </div>

        {/* Filters */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
          {[
            { key: "all", label: "All Posts", count: stats.total },
            { key: "draft", label: "Ready", count: stats.draft },
            { key: "used", label: "Used", count: stats.used },
          ].map((filter) => (
            <button
              key={filter.key}
              onClick={() => setFilterStatus(filter.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap flex items-center gap-2 ${
                filterStatus === filter.key
                  ? "bg-blue-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-slate-300"
              }`}
            >
              {filter.label}
              <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                filterStatus === filter.key
                  ? "bg-blue-500 text-white"
                  : "bg-slate-700 text-slate-500"
              }`}>
                {filter.count}
              </span>
            </button>
          ))}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="space-y-4">
            <PostSkeleton />
            <PostSkeleton />
            <PostSkeleton />
          </div>
        )}

        {/* Empty State */}
        {!loading && filteredPosts.length === 0 && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-12 text-center">
            <div className="w-16 h-16 bg-slate-700/50 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg
                className="w-8 h-8 text-slate-500"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              {filterStatus === "all" ? "No posts yet" : `No ${filterStatus} posts`}
            </h3>
            <p className="text-slate-400 mb-6 max-w-sm mx-auto">
              {filterStatus === "all" 
                ? "Generate your first batch of LinkedIn posts to get started"
                : "Change the filter to see other posts"}
            </p>
            {filterStatus === "all" && (
              <Link
                href="/settings"
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Generate Posts
              </Link>
            )}
          </div>
        )}

        {/* Posts List */}
        {!loading && filteredPosts.length > 0 && (
          <div className="space-y-4">
            {filteredPosts.map((post) => (
              <div
                key={post.id}
                className={`bg-slate-800/50 border rounded-2xl overflow-hidden transition-all ${
                  post.status === "used" 
                    ? "border-green-500/30 bg-green-500/5" 
                    : "border-slate-700 hover:border-slate-600"
                }`}
              >
                {/* Post Header */}
                <div className="flex items-center justify-between px-5 py-3 border-b border-slate-700/50">
                  <div className="flex items-center gap-2">
                    {getStatusBadge(post.status)}
                    {post.sourceArticleUrl && (
                      <span className="text-xs text-slate-500">
                        via {(() => {
                          try {
                            return new URL(post.sourceArticleUrl).hostname.replace('www.', '');
                          } catch {
                            return 'article';
                          }
                        })()}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toggleUsed(post)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        post.status === "used"
                          ? "bg-slate-700 text-slate-300 hover:bg-slate-600"
                          : "bg-green-600/20 text-green-400 hover:bg-green-600/30 border border-green-500/30"
                      }`}
                    >
                      {post.status === "used" ? "Unmark" : "Mark Used"}
                    </button>
                    
                    <button
                      onClick={() => copyPost(post.id, post.content)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        copied === post.id
                          ? "bg-green-600 text-white"
                          : "bg-blue-600 hover:bg-blue-700 text-white"
                      }`}
                    >
                      {copied === post.id ? "✓ Copied!" : "Copy"}
                    </button>
                    
                    <Link
                      href={`/posts/${post.id}`}
                      className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-xs font-medium transition-colors"
                    >
                      Edit
                    </Link>

                    <button
                      onClick={() => deletePost(post.id)}
                      className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                      title="Delete post"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
                
                {/* Source Article Preview */}
                {post.sourceArticleTitle && (
                  <div className="mx-5 mt-4">
                    <a 
                      href={post.sourceArticleUrl || "#"} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="block border border-slate-600 rounded-xl overflow-hidden hover:border-slate-500 transition-colors bg-slate-800/50"
                    >
                      {post.sourceArticleImage && (
                        <div className="relative w-full h-40 bg-slate-700">
                          <img 
                            src={post.sourceArticleImage} 
                            alt={post.sourceArticleTitle}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              (e.target as HTMLImageElement).style.display = 'none';
                            }}
                          />
                        </div>
                      )}
                      <div className="p-3">
                        <h4 className="text-sm font-medium text-slate-200 line-clamp-2 leading-tight">
                          {post.sourceArticleTitle}
                        </h4>
                      </div>
                    </a>
                  </div>
                )}

                {/* Post Content */}
                <div className="px-5 py-4">
                  <div className="whitespace-pre-wrap text-slate-300 leading-relaxed text-[15px]">
                    {post.content}
                  </div>
                </div>
                
                {/* Post Footer */}
                <div className="px-5 py-2.5 bg-slate-900/30 flex items-center justify-between text-xs text-slate-500">
                  <span>
                    {new Date(post.createdAt).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      hour: "numeric",
                      minute: "2-digit",
                    })}
                  </span>
                  {post.audience && (
                    <span className="text-slate-600">
                      {AUDIENCE_LABELS[post.audience] || post.audience}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
