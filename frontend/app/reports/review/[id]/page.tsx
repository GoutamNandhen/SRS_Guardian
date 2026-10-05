import { redirect } from "next/navigation";

interface PageProps {
  params: {
    id: string;
  };
}

export default function DocumentReviewRedirect({ params }: PageProps) {
  redirect(`/reports/review?doc=${params.id}`);
}
