package com.yilu.xundian

import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.view.MotionEvent
import android.view.View
import kotlin.math.min

/** Draws engine state. Hit testing and steps go through `yilu_touch_to_cell` / `yilu_try_step`. */
class BoardView(context: Context) : View(context) {
    var onChange: (() -> Unit)? = null
    private var lastX = Int.MIN_VALUE
    private var lastY = Int.MIN_VALUE
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG)
    private val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = INK
        textAlign = Paint.Align.CENTER
    }
    private val touchOut = IntArray(2)
    private val wallOut = IntArray(4)
    private val pathOut = IntArray(2)

    override fun onDraw(canvas: Canvas) {
        canvas.drawColor(PAPER)
        if (YiluZip.nativeReady() != 1) {
            return
        }
        val metrics = metrics() ?: return
        drawCells(canvas, metrics)
        drawGrid(canvas, metrics)
        drawWalls(canvas, metrics)
        drawPath(canvas, metrics)
        drawNumbers(canvas, metrics)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                lastX = Int.MIN_VALUE
                lastY = Int.MIN_VALUE
                apply(event.x, event.y)
            }
            MotionEvent.ACTION_MOVE -> apply(event.x, event.y)
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                lastX = Int.MIN_VALUE
                lastY = Int.MIN_VALUE
            }
        }
        return true
    }

    private fun apply(px: Float, py: Float) {
        val metrics = metrics() ?: return
        if (metrics.cell <= 0f) {
            return
        }
        val hit = YiluZip.nativeTouch(
            px.toDouble(),
            py.toDouble(),
            metrics.originX.toDouble(),
            metrics.originY.toDouble(),
            metrics.cell.toDouble(),
            touchOut
        )
        if (hit != 1) {
            return
        }
        val x = touchOut[0]
        val y = touchOut[1]
        if (x == lastX && y == lastY) {
            return
        }
        lastX = x
        lastY = y
        YiluZip.nativeTryStep(x, y)
        invalidate()
        onChange?.invoke()
    }

    private fun metrics(): Metrics? {
        val cols = YiluZip.nativeCols()
        val rows = YiluZip.nativeRows()
        if (cols <= 0 || rows <= 0 || width < 2 || height < 2) {
            return null
        }
        val pad = 12f * resources.displayMetrics.density
        val availW = width - pad * 2f
        val availH = height - pad * 2f
        if (availW <= 0f || availH <= 0f) {
            return null
        }
        val cell = min(availW / cols, availH / rows)
        val gridW = cell * cols
        val gridH = cell * rows
        return Metrics(
            (width - gridW) / 2f,
            (height - gridH) / 2f,
            cell,
            cols,
            rows
        )
    }

    private fun drawCells(canvas: Canvas, m: Metrics) {
        val next = YiluZip.nativeNextRequired()
        for (y in 0 until m.rows) {
            for (x in 0 until m.cols) {
                val rect = cellRect(x, y, m)
                fill.style = Paint.Style.FILL
                fill.color = WHITE_PAPER
                canvas.drawRect(rect[0], rect[1], rect[2], rect[3], fill)
                val n = YiluZip.nativeNumberAt(x, y)
                if (n != 0 && n == next) {
                    stroke.color = GOLD
                    stroke.strokeWidth = 1f * resources.displayMetrics.density
                    canvas.drawRect(rect[0] + 4f, rect[1] + 4f, rect[2] - 4f, rect[3] - 4f, stroke)
                }
            }
        }
    }

    private fun drawGrid(canvas: Canvas, m: Metrics) {
        stroke.color = PAPER_LINE
        stroke.strokeWidth = 1f * resources.displayMetrics.density
        for (c in 0..m.cols) {
            val x = m.originX + c * m.cell
            canvas.drawLine(x, m.originY, x, m.originY + m.rows * m.cell, stroke)
        }
        for (r in 0..m.rows) {
            val y = m.originY + r * m.cell
            canvas.drawLine(m.originX, y, m.originX + m.cols * m.cell, y, stroke)
        }
    }

    private fun drawWalls(canvas: Canvas, m: Metrics) {
        val count = YiluZip.nativeWallCount()
        stroke.color = INK
        stroke.strokeWidth = maxOf(3f, m.cell * 0.12f)
        stroke.strokeCap = Paint.Cap.ROUND
        for (i in 0 until count) {
            if (YiluZip.nativeWallAt(i, wallOut) != 1) {
                continue
            }
            val x1 = wallOut[0]
            val y1 = wallOut[1]
            val x2 = wallOut[2]
            val y2 = wallOut[3]
            if (y1 == y2) {
                val left = minOf(x1, x2)
                val x = m.originX + (left + 1) * m.cell
                val y = m.originY + y1 * m.cell
                canvas.drawLine(x, y + m.cell * 0.12f, x, y + m.cell * 0.88f, stroke)
            } else if (x1 == x2) {
                val top = minOf(y1, y2)
                val x = m.originX + x1 * m.cell
                val y = m.originY + (top + 1) * m.cell
                canvas.drawLine(x + m.cell * 0.12f, y, x + m.cell * 0.88f, y, stroke)
            }
        }
    }

    private fun drawPath(canvas: Canvas, m: Metrics) {
        val count = YiluZip.nativePathLen()
        fill.style = Paint.Style.FILL
        fill.color = QING
        for (i in 0 until count) {
            if (YiluZip.nativePathAt(i, pathOut) != 1) {
                continue
            }
            val inset = m.cell * 0.18f
            val rect = cellRect(pathOut[0], pathOut[1], m)
            canvas.drawRect(rect[0] + inset, rect[1] + inset, rect[2] - inset, rect[3] - inset, fill)
        }
        stroke.color = PATH
        stroke.strokeWidth = maxOf(4f, m.cell * 0.16f)
        stroke.strokeCap = Paint.Cap.ROUND
        stroke.strokeJoin = Paint.Join.ROUND
        var started = false
        for (i in 0 until count) {
            if (YiluZip.nativePathAt(i, pathOut) != 1) {
                continue
            }
            val cx = m.originX + (pathOut[0] + 0.5f) * m.cell
            val cy = m.originY + (pathOut[1] + 0.5f) * m.cell
            if (!started) {
                pathLine.reset()
                pathLine.moveTo(cx, cy)
                started = true
            } else {
                pathLine.lineTo(cx, cy)
            }
        }
        if (started) {
            canvas.drawPath(pathLine, stroke)
        }
    }

    private val pathLine = android.graphics.Path()

    private fun drawNumbers(canvas: Canvas, m: Metrics) {
        text.color = INK
        text.textSize = maxOf(12f * resources.displayMetrics.density, m.cell * 0.42f)
        val fm = text.fontMetrics
        val dy = -(fm.ascent + fm.descent) / 2f
        for (y in 0 until m.rows) {
            for (x in 0 until m.cols) {
                val n = YiluZip.nativeNumberAt(x, y)
                if (n == 0) {
                    continue
                }
                val cx = m.originX + (x + 0.5f) * m.cell
                val cy = m.originY + (y + 0.5f) * m.cell
                canvas.drawText(n.toString(), cx, cy + dy, text)
            }
        }
    }

    private fun cellRect(x: Int, y: Int, m: Metrics): FloatArray {
        val left = m.originX + x * m.cell
        val top = m.originY + y * m.cell
        return floatArrayOf(left + 1f, top + 1f, left + m.cell - 1f, top + m.cell - 1f)
    }

    private class Metrics(
        val originX: Float,
        val originY: Float,
        val cell: Float,
        val cols: Int,
        val rows: Int
    )

    companion object {
        /* Tokens from the repo README「设计师 token」table. */
        private const val PAPER = 0xFFF3E8D6.toInt()
        private const val PAPER_LINE = 0xFFD4C4A8.toInt()
        private const val INK = 0xFF2C2A26.toInt()
        private const val QING = 0xFF6B7A78.toInt()
        private const val PATH = 0xFF3F4F4C.toInt()
        private const val GOLD = 0xFFC4A35A.toInt()
        private const val WHITE_PAPER = 0xFFFBF6EC.toInt()
    }
}
