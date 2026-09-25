export function Hint({ children }) {
  return (
    <details className="hint">
      <summary>Как читать</summary>
      <p>{children}</p>
    </details>
  );
}
