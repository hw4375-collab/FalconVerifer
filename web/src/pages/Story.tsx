import { loadBench, useAsync } from '../lib/data'
import { CounterModel } from '../story/CounterModel'
import { Grammar } from '../story/Grammar'
import { Hero } from '../story/Hero'
import { Close, Lesson } from '../story/Lesson'
import { Loop } from '../story/Loop'
import { Outcome } from '../story/Outcome'
import { Problem } from '../story/Problem'

export function Story() {
  const { data } = useAsync(loadBench)
  const arm = data?.arms.find((a) => a.key === 'falcon3b_arabic')
  const scale = data?.arms.find((a) => a.key === 'falcon3b_arabic_scale')

  return (
    <main>
      <Hero />
      {arm ? <Problem arm={arm} /> : <div className="h-[80vh]" />}
      <Loop />
      <Grammar />
      <CounterModel />
      {arm ? <Outcome arm={arm} scale={scale} /> : <div className="h-[90vh]" />}
      <Lesson />
      <Close />
    </main>
  )
}
