import React from 'react';
import { Link } from 'react-router-dom';
import { Layers, Settings, Database, ArrowLeft, Clock, Compass } from 'lucide-react';

const sectionMetadata = {
  Sectors: {
    icon: Layers,
    badge: 'Roadmap Milestone',
    tagline: 'Multi-Timeframe Sector Rotation & Heatmap',
    description:
      'Aggregated sector breadth, relative strength rotation matrix, and NIFTY sub-index momentum analysis are scheduled for a dedicated roadmap phase. Currently, key sector relative strength metrics are tracked directly on the main Dashboard.',
    dashboardLinkText: 'View Sector Ratios on Dashboard',
  },
  Settings: {
    icon: Settings,
    badge: 'Preferences',
    tagline: 'Application & Notification Configuration',
    description:
      'Custom risk tolerance thresholds, alert parameters, and API configuration options will be available in future releases. Theme and view preferences are already active in your current session.',
    dashboardLinkText: 'Return to Dashboard',
  },
  'Data Health': {
    icon: Database,
    badge: 'System Pipeline',
    tagline: 'Daily EOD Ingestion & Validation Monitor',
    description:
      'The automated end-of-day data pipeline syncs 50 liquid Indian equities daily with verifiable OHLCV and indicator health checks. Live pipeline status is summarized on the main Dashboard.',
    dashboardLinkText: 'Check Data Health on Dashboard',
  },
};

const PlaceholderPage = ({ title = 'Planned Capability' }) => {
  const meta = sectionMetadata[title] || {
    icon: Compass,
    badge: 'Planned Capability',
    tagline: 'Future Enhancement',
    description: 'This capability is planned for an upcoming release of Swing-tool.',
    dashboardLinkText: 'Return to Dashboard',
  };

  const Icon = meta.icon;

  return (
    <div className="p-4 sm:p-8 max-w-4xl mx-auto flex flex-col items-center justify-center min-h-[calc(100vh-140px)] text-center animate-fade-in">
      <div className="w-full bg-surface border border-border-primary rounded-3xl p-8 sm:p-12 shadow-sm flex flex-col items-center">
        <div className="w-16 h-16 rounded-2xl bg-accent-teal/10 text-accent-teal flex items-center justify-center mb-6 border border-accent-teal/20">
          <Icon className="w-8 h-8" />
        </div>

        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-accent-teal/10 text-accent-teal border border-accent-teal/20 mb-4">
          <Clock className="w-3.5 h-3.5" />
          <span>{meta.badge}</span>
        </div>

        <h1 className="text-2xl sm:text-3xl font-heading font-bold text-tx-primary tracking-tight mb-2">
          {title}
        </h1>

        <p className="text-sm font-medium text-accent-green mb-4">
          {meta.tagline}
        </p>

        <p className="text-sm text-tx-secondary max-w-xl leading-relaxed mb-8">
          {meta.description}
        </p>

        <div className="flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-accent-green hover:bg-accent-green/90 text-surface text-sm font-semibold transition-colors shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>{meta.dashboardLinkText}</span>
          </Link>
          <Link
            to="/opportunities"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-surface-secondary hover:bg-surface-secondary/80 text-tx-primary text-sm font-medium border border-border-primary transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-green"
          >
            <span>Explore Opportunities</span>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default PlaceholderPage;
