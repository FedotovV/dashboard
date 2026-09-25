import { num } from "../format.js";
import { reasonLabel } from "../labels.js";
import { IssueLink } from "./IssueLink.jsx";
import { Hint } from "./Hint.jsx";

export function Issues({ view }) {
  const showPoints = view?.coverage?.storyPoints !== "off";
  const issues = view?.sprint?.issues || [];
  return (
    <section data-widget="issues">
      <h2>Задачи</h2>
      <Hint>Ключ открывает задачу в Jira. Выделены срок, если он просрочен, причина блокера и пустая оценка.</Hint>
      <table>
        <thead>
          <tr>
            <th>Ключ</th>
            <th>Название</th>
            <th>Статус</th>
            <th>Исполнитель</th>
            <th>Состав</th>
            <th>Блокеры</th>
            <th>Срок</th>
            {showPoints ? <th data-column="storyPoints">Story points</th> : null}
          </tr>
        </thead>
        <tbody>
          {issues.map((issue) => {
            const reasons = issue.blockerReasons || [];
            const reasonText = reasons.map((reason) => reasonLabel(reason)).join(", ");
            let due = issue.dueDate || "";
            if (issue.closedBeforeDue === true) {
              due = `${due} раньше срока`.trim();
            }
            return (
              <tr key={issue.key}>
                <td><IssueLink view={view} issueKey={issue.key} /></td>
                <td>{issue.summary ?? ""}</td>
                <td>{issue.status ?? ""}</td>
                <td>{issue.assigneeId ?? ""}</td>
                <td>{issue.scope ?? ""}</td>
                <td {...(reasons.length > 0 ? { "data-attention": "true" } : {})}>{reasonText}</td>
                <td {...(reasons.includes("overdue") ? { "data-attention": "true" } : {})}>{due}</td>
                {showPoints ? (
                  <td {...(issue.storyPoints == null ? { "data-attention": "true" } : {})}>{num(issue.storyPoints)}</td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
