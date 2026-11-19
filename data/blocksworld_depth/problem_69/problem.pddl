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
		(ontable orange)
		(on red orange)
		(on green red)
		(clear green)

		(ontable purple)
		(clear purple)
		(ontable yellow)
		(on blue yellow)
		(clear blue)
	)
	(:goal (and (handempty robot)
		(ontable blue)
		(clear blue)
		(ontable yellow)
		(on green yellow)
		(clear green)

		(ontable orange)
		(on purple orange)
		(on red purple)
		(clear red)
	))
)