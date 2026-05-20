export default function PricingCard({
  name,
  price,
  limit,
  features,
  action,
  onAction,
}: {
  name: string;
  price: string;
  limit: string;
  features: string[];
  action: string;
  onAction: () => void;
}) {
  return (
    <article className="panel flex h-full flex-col p-5">
      <h2 className="text-2xl font-black text-[#10213f]">{name}</h2>
      <div className="mt-3 text-3xl font-black text-[#1459d9]">{price}</div>
      <p className="mt-2 text-sm font-black text-[#52647f]">{limit}</p>
      <ul className="my-6 space-y-2 text-sm font-semibold text-[#3c4e68]">
        {features.map((feature) => (
          <li key={feature}>{feature}</li>
        ))}
      </ul>
      <button className="btn-primary mt-auto" onClick={onAction}>
        {action}
      </button>
    </article>
  );
}
