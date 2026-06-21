import { LandingNav } from "@/components/landing/LandingNav";
import { LandingHero } from "@/components/landing/LandingHero";
import { ProductPreview } from "@/components/landing/ProductPreview";
import { PlatformSection } from "@/components/landing/PlatformSection";
import { HowItWorksSection } from "@/components/landing/HowItWorksSection";
import { CapabilitiesSection } from "@/components/landing/CapabilitiesSection";
import { TrustSection } from "@/components/landing/TrustSection";
import { LandingFooter } from "@/components/landing/LandingFooter";

const Landing = () => {
  return (
    <div className="landing-page min-h-screen">
      <LandingNav />
      <main>
        <LandingHero />
        <ProductPreview />
        <PlatformSection />
        <HowItWorksSection />
        <CapabilitiesSection />
        <TrustSection />
      </main>
      <LandingFooter />
    </div>
  );
};

export default Landing;
