export default function IconButton({ icon, onClick, title, disabled }) {
  return (
    <button
      className="icon-btn"
      onClick={onClick}
      title={title}
      disabled={disabled}
    >
      <img src={icon} alt={title} style={{ width: '1em', height: '1em' }} />
    </button>
  );
}
