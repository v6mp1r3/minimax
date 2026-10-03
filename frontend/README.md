# DocuGuide frontend

React + Vite. `npm install`, then `npm run dev` (proxies `/api` to the backend on :8000)
or `npm run build` (output in `dist/`, served by FastAPI).

```
src/
├── main.jsx                     entry point
├── App.jsx                      page switching (home / category / chat)
├── components/                  shared UI: Icon (icon registry), Logo, Navbar, Avatar, ConfirmDialog
├── data/categories.js           categories, example questions, backend→UI category map
├── lib/
│   ├── api.js                   the only code that calls /api/chat (+ readable error messages)
│   └── storage.js               localStorage: conversation history and document checklist
├── hooks/
│   ├── useChat.js               conversation state + request flow (answer / follow-up / questions)
│   ├── useChatHistory.js        saved conversations: pin, delete, current chat id
│   └── useSpeechRecognition.js  dictation (Web Speech API)
├── pages/
│   ├── HomePage.jsx, CategoryPage.jsx
│   └── chat/
│       ├── ChatPage.jsx         wires the hooks to the pieces below
│       ├── ChatSidebar.jsx, ChatHeader.jsx, MessageList.jsx, Composer.jsx
│       ├── ThinkingBubble.jsx   the "typing" dots
│       └── answers/             AnswerCard, StepList, DocumentList, FollowupCard, QuestionCard, SourceParts
└── styles/
    └── index.css                imports every stylesheet, in order
```

Styles: the files in `styles/` are loaded in the order listed in `styles/index.css`.
Later files refine earlier ones (same selectors), so keep that order when adding or moving rules.
Icons: add a glyph once in `components/Icon.jsx`, then use `<Icon name="..." />`.
