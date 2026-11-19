(define (problem blocksworld)
	(:domain blocksworld)
	(:objects
		blue - block
		green - block
		orange - block
		purple - block
		red - block
		yellow - block
		robot - robot
	)
	(:init (handempty robot)
		(ontable yellow)
		(clear yellow)
		(ontable orange)
		(on purple orange)
		(clear purple)

		(ontable green)
		(on red green)
		(on blue red)
		(clear blue)
	)
	(:goal (and (handempty robot)
		(ontable orange)
		(on red orange)
		(on green red)
		(clear green)

		(ontable purple)
		(clear purple)
		(ontable yellow)
		(on blue yellow)
		(clear blue)
	))
)