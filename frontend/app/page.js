import { redirect } from "next/navigation";
import { fetchBoundary } from "@/lib/api";

export default function RootPage() {
  redirect("/dashboard");
}
