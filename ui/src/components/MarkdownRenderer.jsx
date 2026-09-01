import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error("Markdown rendering error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="text-neutral-400 text-xs whitespace-pre-wrap font-mono">
          {this.props.fallbackContent || "Error rendering markdown."}
        </div>
      );
    }
    return this.props.children;
  }
}

const MarkdownRenderer = ({ content, isStreaming, className = "" }) => {
  return (
    <ErrorBoundary fallbackContent={content}>
      <div className={`markdown-body ${className}`}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            h1: ({node, ...props}) => <h1 className="text-emerald-300 font-semibold text-xs uppercase tracking-wider mt-3 mb-1.5 first:mt-0" {...props} />,
            h2: ({node, ...props}) => <h2 className="text-emerald-300 font-semibold text-xs uppercase tracking-wider mt-3 mb-1.5 first:mt-0" {...props} />,
            h3: ({node, ...props}) => <h3 className="text-neutral-200 font-medium text-xs mt-2 mb-1" {...props} />,
            h4: ({node, ...props}) => <h4 className="text-neutral-200 font-medium text-xs mt-2 mb-1" {...props} />,
            p: ({node, ...props}) => <p className="text-neutral-300 text-xs leading-relaxed my-1" {...props} />,
            ul: ({node, ...props}) => <ul className="list-disc list-outside pl-4 my-1.5 space-y-1 text-neutral-300 text-xs" {...props} />,
            ol: ({node, ...props}) => <ol className="list-decimal list-outside pl-4 my-1.5 space-y-1 text-neutral-300 text-xs" {...props} />,
            li: ({node, ...props}) => <li className="text-neutral-300 text-xs leading-relaxed pl-0.5" {...props} />,
            strong: ({node, ...props}) => <strong className="text-neutral-100 font-semibold" {...props} />,
            code: ({node, inline, ...props}) => 
              inline ? 
                <code className="px-1 py-0.5 rounded bg-neutral-800/80 text-emerald-300 font-mono text-[11px]" {...props} /> :
                <pre className="px-2 py-1 rounded bg-neutral-800/80 text-emerald-300 font-mono text-[11px] overflow-x-auto my-1"><code {...props} /></pre>,
            a: ({node, ...props}) => <span className="text-emerald-400/80 underline decoration-emerald-400/30 underline-offset-2" {...props} />
          }}
        >
          {content}
        </ReactMarkdown>
        {isStreaming && (
          <span className="inline-block w-1.5 h-3 ml-1 bg-emerald-400 animate-pulse align-middle" />
        )}
      </div>
    </ErrorBoundary>
  );
};

export default MarkdownRenderer;
