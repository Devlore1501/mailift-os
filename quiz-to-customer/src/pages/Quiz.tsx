import { useEffect } from "react";
import EmailMarketingSurvey from "@/components/EmailMarketingSurvey";

const Quiz = () => {
  useEffect(() => {
    // Re-fire PageView for SPA navigation (React Router doesn't reload HTML)
    window.fbq?.('track', 'PageView');
    // Lead fires ONLY if user came from landing page opt-in (?email= in URL).
    // If no email param, the user arrived directly or from a Facebook native lead form
    // which already counted the lead onsite — firing here would double-count.
    const hasEmailParam = new URLSearchParams(window.location.search).has('email');
    if (hasEmailParam) {
      window.fbq?.('track', 'Lead');
    }
    window.fbq?.('trackCustom', 'QuizPageView');
  }, []);

  return <EmailMarketingSurvey skipIntro />;
};

export default Quiz;
