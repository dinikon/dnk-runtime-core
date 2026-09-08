import { runFixture } from "./fixture";

export default function teardown() {
  runFixture("cleanup");
}
