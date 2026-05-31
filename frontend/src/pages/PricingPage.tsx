import { useState } from "react";
import Footer from "../components/Footer";
import Navbar from "../components/Navbar";
import PricingCard from "../components/PricingCard";

export default function PricingPage() {
  const [notice, setNotice] = useState("");
  const notify = (planName: string) => {
    setNotice(`${planName} plan changes are placeholders until billing integration is connected.`);
  };

  return (
    <div>
      <Navbar />
      <main className="shell py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black text-[#10213f]">Pricing</h1>
          <p className="mt-2 text-sm font-semibold text-[#52647f]">
            Choose a plan that fits your PDF workflow. Checkout is not connected yet, so upgrade and downgrade actions are placeholders.
          </p>
        </div>
        {notice ? <div className="mb-5 rounded-lg border border-[#b8e2c8] bg-[#effaf3] p-4 text-sm font-black text-[#17633a]">{notice}</div> : null}
        <div className="grid gap-4 md:grid-cols-3">
          <PricingCard name="Free" price="₹0" limit="5 PDFs/month" features={["Basic PDF generation", "Downgrade placeholder"]} action="Use Free" onAction={() => notify("Free")} />
          <PricingCard name="Pro" price="₹299/month" limit="100 PDFs/month" features={["Priority generation", "Upgrade placeholder"]} action="Upgrade to Pro" onAction={() => notify("Pro")} />
          <PricingCard name="Business" price="₹999/month" limit="1000 PDFs/month" features={["Team-ready usage", "Sales handoff placeholder"]} action="Contact Sales" onAction={() => notify("Business")} />
        </div>
      </main>
      <Footer />
    </div>
  );
}
