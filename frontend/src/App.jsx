import { useEffect, useState } from "react";
import { Navbar } from "./components/Navbar.jsx";
import { CategoryPage } from "./pages/CategoryPage.jsx";
import { HomePage } from "./pages/HomePage.jsx";
import { ChatPage } from "./pages/chat/ChatPage.jsx";

function App() {
  const [page, setPage] = useState("home");
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [initialMessage, setInitialMessage] = useState("");

  const openChat = (text = "") => {
    setInitialMessage(text);
    setPage("chat");
  };

  const openCategory = (category) => {
    setSelectedCategory(category);
    setPage("category");
  };

  const goHome = () => setPage("home");

  // every page switch starts at the top, so the navbar/logo never appears shifted
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [page]);

  return (
    <div className="app">
      {page !== "chat" && <Navbar onHome={goHome} onChat={() => openChat("")} />}

      {page === "home" && <HomePage onChat={openChat} onCategory={openCategory} />}

      {page === "category" && (
        <CategoryPage category={selectedCategory} onChat={openChat} onHome={goHome} />
      )}

      {page === "chat" && (
        <ChatPage key={initialMessage} initialMessage={initialMessage} onHome={goHome} />
      )}
    </div>
  );
}

export default App;
