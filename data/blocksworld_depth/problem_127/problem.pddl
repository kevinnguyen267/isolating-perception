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
		(clear orange)
		(ontable yellow)
		(on green yellow)
		(clear green)

		(ontable blue)
		(clear blue)
		(ontable red)
		(on purple red)
		(clear purple)
	)
	(:goal (and (handempty robot)
		(ontable purple)
		(clear purple)
		(ontable red)
		(on green red)
		(clear green)

		(ontable orange)
		(on blue orange)
		(clear blue)
		(ontable yellow)
		(clear yellow)
	))
)