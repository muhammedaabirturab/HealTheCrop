import HeroSection from '../components/landing/HeroSection'
import AboutSection from '../components/landing/AboutSection'
import HowItWorksSection from '../components/landing/HowItWorksSection'
import FeaturesSection from '../components/landing/FeaturesSection'
import WhyUseSection from '../components/landing/WhyUseSection'
import AISection from '../components/landing/AISection'

export default function Landing() {
  return (
    <div className="flex-1 flex flex-col">
      <HeroSection />
      <AboutSection />
      <HowItWorksSection />
      <FeaturesSection />
      <WhyUseSection />
      <AISection />
    </div>
  )
}
