import type { EngineInfo } from "@aiview/shared-types";
import { useEffect, useState } from "react";
import { fetchSettings, putSettings } from "../api/engine";

/** F9 — ต้องยอมรับก่อนใช้ครั้งแรก (เก็บใน engine settings) */
export default function DisclaimerModal({ info }: { info: EngineInfo | null }) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!info) return;
    let cancelled = false;
    fetchSettings(info)
      .then((s) => {
        if (!cancelled && !s["disclaimer_accepted"]) setShow(true);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [info]);

  if (!show) return null;

  const accept = async () => {
    if (info) await putSettings(info, { disclaimer_accepted: true });
    setShow(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70"
         data-testid="disclaimer-modal">
      <div className="w-[480px] rounded-xl border border-slate-700 bg-slate-900 p-6">
        <h2 className="mb-3 text-lg font-bold text-slate-100">⚠️ ข้อจำกัดความรับผิดชอบ</h2>
        <div className="space-y-2 text-sm leading-relaxed text-slate-300">
          <p>
            AIView by ET เป็น<strong>เครื่องมือวิเคราะห์เพื่อการศึกษา</strong>เท่านั้น —
            <strong> ไม่ใช่คำแนะนำการลงทุน</strong>
          </p>
          <p>
            การเทรดฟิวเจอร์สมีความเสี่ยงสูง อาจสูญเสียเงินต้นทั้งหมด · signal จาก AI
            และผลจากการจำลอง/backtest <strong>ไม่รับประกันผลลัพธ์ในอนาคต</strong>
          </p>
          <p>ทุกการตัดสินใจลงทุนเป็นความรับผิดชอบของผู้ใช้เอง</p>
        </div>
        <button
          onClick={accept}
          className="mt-4 w-full rounded bg-cyan-600 py-2 text-sm font-semibold text-white hover:bg-cyan-500"
        >
          เข้าใจและยอมรับ
        </button>
      </div>
    </div>
  );
}
