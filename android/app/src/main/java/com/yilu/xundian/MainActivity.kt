package com.yilu.xundian

import android.app.Activity
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

class MainActivity : Activity() {
    private lateinit var nameLabel: TextView
    private lateinit var statusLabel: TextView
    private lateinit var board: BoardView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val paper = Color.parseColor("#F3E8D6")
        val ink = Color.parseColor("#2C2A26")
        window.decorView.setBackgroundColor(paper)

        try {
            YiluZip.prepare(this)
        } catch (error: Throwable) {
            setContentView(messageView(error.message ?: "native load failed", ink, paper))
            return
        }
        val loadError = try {
            YiluZip.loadAssetLevel(this)
        } catch (error: Throwable) {
            error.message ?: "level.json failed"
        }
        if (loadError != null) {
            setContentView(messageView(loadError, ink, paper))
            return
        }

        val title = TextView(this).apply {
            text = "驿路巡点"
            textSize = 28f
            setTextColor(ink)
            gravity = Gravity.CENTER
        }
        nameLabel = TextView(this).apply {
            textSize = 17f
            setTextColor(ink)
            gravity = Gravity.CENTER
        }
        statusLabel = TextView(this).apply {
            textSize = 15f
            setTextColor(ink)
            gravity = Gravity.CENTER
        }
        board = BoardView(this).apply {
            onChange = { refresh() }
        }
        val undo = Button(this).apply {
            text = "撤销"
            setOnClickListener {
                YiluZip.nativeUndo()
                board.invalidate()
                refresh()
            }
        }
        val clear = Button(this).apply {
            text = "重绘驿道"
            setOnClickListener {
                YiluZip.nativeClear()
                board.invalidate()
                refresh()
            }
        }
        val buttons = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            addView(undo, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(clear, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        }
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(12), dp(16), dp(12))
            setBackgroundColor(paper)
            addView(title)
            addView(nameLabel)
            addView(statusLabel)
            addView(board, LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f
            ))
            addView(buttons)
        }
        setContentView(column)
        refresh()
    }

    private fun refresh() {
        nameLabel.text = "${YiluZip.levelName()} · id ${YiluZip.nativeLevelId()}"
        statusLabel.text = if (YiluZip.nativeIsWin() == 1) {
            "通关"
        } else {
            "第 ${YiluZip.nativeFilled()} 步 · 下一驿 ${YiluZip.nativeNextRequired()}"
        }
    }

    private fun messageView(message: String, ink: Int, paper: Int): TextView {
        return TextView(this).apply {
            text = message
            textSize = 16f
            setTextColor(ink)
            setBackgroundColor(paper)
            gravity = Gravity.CENTER
            setPadding(dp(24), dp(24), dp(24), dp(24))
        }
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }
}
