import { TopNavigation } from "./TopNavigation";

export function Header() {
  return (
    <header className="app-header">
      <div className="app-header__inner">
        <p className="app-title">Enterprise KnowledgeOps Studio</p>
        <TopNavigation />
      </div>
    </header>
  );
}
