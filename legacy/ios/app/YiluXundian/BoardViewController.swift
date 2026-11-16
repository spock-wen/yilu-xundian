import UIKit

final class BoardViewController: UIViewController {
    private let zip = YiluZip()
    private let titleLabel = UILabel()
    private let nameLabel = UILabel()
    private let statusLabel = UILabel()
    private let board = BoardView()
    private let undoButton = UIButton(type: .system)
    private let clearButton = UIButton(type: .system)

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = BoardPalette.paper
        if #available(iOS 13.0, *) {
            overrideUserInterfaceStyle = .light
        }
        titleLabel.text = "驿路巡点"
        titleLabel.font = UIFont.systemFont(ofSize: 28, weight: .semibold)
        titleLabel.textColor = BoardPalette.ink
        titleLabel.textAlignment = .center

        nameLabel.font = UIFont.systemFont(ofSize: 17, weight: .regular)
        nameLabel.textColor = BoardPalette.ink
        nameLabel.textAlignment = .center
        nameLabel.numberOfLines = 2

        statusLabel.font = UIFont.systemFont(ofSize: 15, weight: .regular)
        statusLabel.textColor = BoardPalette.ink
        statusLabel.textAlignment = .center
        statusLabel.numberOfLines = 2

        undoButton.setTitle("撤销", for: .normal)
        clearButton.setTitle("重绘驿道", for: .normal)
        undoButton.addTarget(self, action: #selector(undoTapped), for: .touchUpInside)
        clearButton.addTarget(self, action: #selector(clearTapped), for: .touchUpInside)
        undoButton.setTitleColor(BoardPalette.ink, for: .normal)
        clearButton.setTitleColor(BoardPalette.ink, for: .normal)
        undoButton.titleLabel?.font = UIFont.systemFont(ofSize: 17, weight: .medium)
        clearButton.titleLabel?.font = UIFont.systemFont(ofSize: 17, weight: .medium)

        let buttons = UIStackView(arrangedSubviews: [undoButton, clearButton])
        buttons.axis = .horizontal
        buttons.distribution = .fillEqually
        buttons.spacing = 12

        let column = UIStackView(arrangedSubviews: [titleLabel, nameLabel, statusLabel, board, buttons])
        column.axis = .vertical
        column.spacing = 8
        column.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(column)

        let guide = view.safeAreaLayoutGuide
        NSLayoutConstraint.activate([
            column.leadingAnchor.constraint(equalTo: guide.leadingAnchor, constant: 16),
            column.trailingAnchor.constraint(equalTo: guide.trailingAnchor, constant: -16),
            column.topAnchor.constraint(equalTo: guide.topAnchor, constant: 12),
            column.bottomAnchor.constraint(equalTo: guide.bottomAnchor, constant: -12),
            undoButton.heightAnchor.constraint(equalToConstant: 44),
            board.heightAnchor.constraint(greaterThanOrEqualToConstant: 240),
        ])

        board.setContentHuggingPriority(.defaultLow, for: .vertical)
        board.onChange = { [weak self] in
            self?.refresh()
        }
        zip.loadBundledLevel()
        refresh()
    }

    @objc private func undoTapped() {
        guard zip.loaded else { return }
        _ = yilu_undo()
        board.setNeedsDisplay()
        refresh()
    }

    @objc private func clearTapped() {
        guard zip.loaded else { return }
        yilu_clear()
        board.setNeedsDisplay()
        refresh()
    }

    private func refresh() {
        if !zip.loaded {
            nameLabel.text = zip.loadError
            statusLabel.text = ""
            undoButton.isEnabled = false
            clearButton.isEnabled = false
            return
        }
        undoButton.isEnabled = true
        clearButton.isEnabled = true
        let name = zip.levelName()
        let id = yilu_level_id()
        nameLabel.text = "\(name) · id \(id)"
        if yilu_is_win() == 1 {
            statusLabel.text = "通关"
        } else {
            let filled = yilu_filled()
            let next = yilu_next_required()
            statusLabel.text = "第 \(filled) 步 · 下一驿 \(next)"
        }
    }
}
