import { Link } from "react-router";

export function NotFoundPage() {
  return (
    <section>
      <h1>Page not found</h1>
      <Link className="link" to="/quotations">
        Go to quotations
      </Link>
    </section>
  );
}
